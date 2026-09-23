"""
This script is responsible for ingesting Real-Time Kinematic (RTK) correction data
in the RTCM format from an NTRIP caster and storing it in the UREGA database.

The script uses asynchronous programming to handle multiple NTRIP streams concurrently.
It connects to the NTRIP caster, receives the RTCM data, and then stores it in the
database.

The script uses the asyncpg library for PostgreSQL database operations and the
ntripstreams library for handling NTRIP streams and RTCM3 data.

The script can be run from the command line and takes arguments for the configuration
settings. The settings include the details for the NTRIP caster and the database.
"""

import asyncio
import json
import logging
import math
import os
import signal
from argparse import ArgumentParser
from multiprocessing import Lock, Manager, Pipe, Process
from multiprocessing.connection import Connection
from time import time

from dotenv import load_dotenv

import decoderclasses
from databasehandling import (
    DatabaseConnection,
    DatabaseHandler,
    NtripLogHandler,
    NtripObservationHandler,
)
from ntripclasses import Caster, Mountpoint
from ntripclient import NtripClients
from rtcm3 import Rtcm3
from settings import DbSettings, MultiprocessingSettings

INIT_GRACEFUL_SHUTDOWN = False

logger = logging.getLogger(__name__)

class SignalHandler:
    """Signal handler for graceful shutdown"""

    def __init__(self, loop, processes = list[Process]):
        self.loop = loop
        self.processes = processes
        for sig in (signal.SIGHUP, signal.SIGTERM, signal.SIGINT):
            self.loop.add_signal_handler(sig, self.shutdown, sig)

    def shutdown(self, sig: signal.Signals) -> None:
        logger.info(f"Received signal {sig.name}. Initiating graceful shutdown.")
        global INIT_GRACEFUL_SHUTDOWN
        INIT_GRACEFUL_SHUTDOWN = True
        for proc in self.processes:
            proc.pipe_write.send(1)
        
        self.loop.stop()


async def watchdogHandler(
    casterSettingsDict: dict,
    mountPointList: list,
    tasks: dict,
    sharedEncoded: list,
    lock,
) -> None:
    try:
        while not INIT_GRACEFUL_SHUTDOWN:
            runningTasks = asyncio.all_tasks()
            runningTasks = [task for task in runningTasks if task.get_name() != "watchdog"]
            runningTaskNames = [runningTask.get_name() for runningTask in runningTasks]

            if len(runningTasks) <= len(mountPointList):
                logger.debug(f"{runningTaskNames} tasks running, {mountPointList} wanted.")
                # For each desired task
                for wantedTask in mountPointList:
                    casterId, mountpoint = wantedTask
                    if mountpoint not in runningTaskNames:
                        casterSettings = casterSettingsDict[casterId]
                        # BROKEN BECAUSE mountpoint HERE IS A STRING, NOT A CLASS INSTANCE
                        tasks[mountpoint] = asyncio.create_task(
                            procRtcmStream(
                                casterSettings,
                                dbSettings,
                                mountpoint,
                                lock,
                                sharedEncoded,
                            ),
                            name=mountpoint,
                        )
                        logger.warning(f"{mountpoint} RTCM stream restarted.")
            
            await asyncio.sleep(30)  # Sleep for 30 seconds
    except asyncio.CancelledError:
        logger.debug(f"Watchdog on loop {id(asyncio.get_running_loop())} closed.") 


def clearList(sharedList):
    del sharedList[:]


async def decodeInsertConsumer(
    sharedEncoded,
    dbSettings: DbSettings,
    lock: Lock,
    pipe_read: Connection,
    fail: int = 0,
    retry: int = 3,
    checkInterval: float = 0.1,
):
    """
    Runs as an asynchronous job.
    """
    dBHandler = None
    rtcmMessage = Rtcm3()

    while True:
        try:
            dBHandler = NtripObservationHandler(dbSettings)
            await dBHandler.initializePool()
            break
        except Exception as error:
            fail += 1
            sleepTime = 5 * fail
            sleepTime = min(sleepTime, 300)
            logger.error(
                "Failed to connect to database server: "
                f"{dbSettings.database}@{dbSettings.host} "
                f"with error: {error}"
            )
            logger.error(
                f"Will retry database connection in {sleepTime} seconds!"
            )
            await asyncio.sleep(sleepTime)
    logger.info(
        f"Connected to database: {dbSettings.database}@{dbSettings.host}."
    )
    try:
        while not pipe_read.poll():
            await asyncio.sleep(checkInterval)
            if sharedEncoded:
                lock.acquire()
                # Perform the list and clearList operations directly in the asyncio event loop
                encodedFramesList = list(sharedEncoded)
                clearList(sharedEncoded)
                lock.release()
                # Loop over all encoded frames and decode and insert the data
                logger.debug(
                    f"Decoding {len(encodedFramesList)} sets of frames with a total of {sum(len(frames) for frames in encodedFramesList)} frames."
                )
                for encodedFrames in encodedFramesList:
                    try:
                        (
                            decodedFrames,
                            decodedObs,
                        ) = await decoderclasses.Decoder.batchDecodeFrame(
                            encodedFrames, dbSettings.storeObservations, rtcmMessage
                        )
                        await dBHandler.dbInsertBatch(
                            decodedFrames, decodedObs
                        )
                    except Exception as error:
                        logger.error(
                            f"An error occurred while batch decoding or batch inserting: {error}"
                        )
    except Exception as error:
        logger.error(f"An error occurred while decoding and appending {error}")
    finally:
        if dBHandler:
            await dBHandler.closePool()
        
        logger.debug(f"decodeInsertConsumer on loop {id(asyncio.get_running_loop())} done.")
            

def mountpointSplitter(casterSettingsDict: dict, maxProcesses: int) -> list:
    """
    Used to split the mountpoints into chunks based on the number of processes to be run.
    Each chunk will run on its own core.

    Args:
        casterSettingsDict (dict): Dictionary of Caster settings
        maxProcesses (int): maximum number of processes to be run

    Returns:
        list: list of lists of Mountpoint instances
    """

    total_mountpoints = sum([len(caster.mountpoints) for caster in casterSettingsDict.values()])
    mountpoints_per_proc = total_mountpoints // maxProcesses + 1

    chunks = []
    chunk = []
    space_in_chunk = mountpoints_per_proc

    for caster in casterSettingsDict.values():
        position_in_caster = 0
        remaining_in_caster = len(caster.mountpoints)
        while remaining_in_caster > 0:
            if space_in_chunk > remaining_in_caster:
                chunk = chunk + caster.mountpoints[position_in_caster:position_in_caster + remaining_in_caster]
                space_in_chunk = space_in_chunk - remaining_in_caster
                position_in_caster = position_in_caster + remaining_in_caster
                remaining_in_caster = 0
            if space_in_chunk <= remaining_in_caster:
                chunk = chunk + caster.mountpoints[position_in_caster:position_in_caster + space_in_chunk]
                chunks.append(chunk)
                chunk = []
                space_in_chunk = mountpoints_per_proc
                position_in_caster = position_in_caster + space_in_chunk
                remaining_in_caster = remaining_in_caster - space_in_chunk

    # add last chunk
    if len(chunk) > 0:
        chunks.append(chunk)

    return chunks


async def appendToList(listToAppend, sharedList, lock):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, lock.acquire)
    try:
        sharedList.append(listToAppend)
    except Exception as error:
        logger.error(f"An error occurred while appending to list: {error}")
    finally:
        lock.release()


async def periodicFrameAppender(
    encodedFrames, sharedEncoded, lock, mountPoint, checkInterval=0.05
):
    while not INIT_GRACEFUL_SHUTDOWN:
        await asyncio.sleep(
            checkInterval
        )  # Wait for a short period to avoid hogging the CPU
        if encodedFrames and (time() - encodedFrames[-1]["time_received"]) > checkInterval:
            try:
                await appendToList(encodedFrames[:], sharedEncoded, lock)
                # logger.debug(
                #     f"{mountPoint}: {len(encodedFrames)} frames collected. Appended to shared memory. {[frame["mountpoint_id"] for frame in encodedFrames]}"
                # )
                encodedFrames.clear()
            except Exception as error:
                logger.error(
                    f"An error occurred in periodic check for appending frames: {error}"
                )
    
    logger.debug(f"periodicFrameAppender on loop {id(asyncio.get_running_loop())} closed.")



async def procRtcmStream(
    casterSettings: Caster,
    dbSettings: DbSettings,
    mountPoint: Mountpoint,
    lock,
    sharedEncoded,
    fail: int = 0,
    retry: int = 3,
) -> None:
    ntripclient = NtripClients()
    ntripLogger = NtripLogHandler(dbSettings, mountPoint.mountpoint)
    await ntripLogger.initializePool()
    ntripclient = await ntripLogger.requestStream(
        ntripclient, casterSettings, log_disconnect=False
    )
    encodedFrames = []

    logger.debug(mountPoint)

    asyncio.create_task(
        periodicFrameAppender(encodedFrames, sharedEncoded, lock, mountPoint.mountpoint)
    )

    try:
        while not INIT_GRACEFUL_SHUTDOWN:
            try:
                frames_in_buffer, timeStamp = await ntripclient.getRtcmFrame()
                for rtcmFrame in frames_in_buffer:
                    encodedFrames.append(
                        {
                            "frame": rtcmFrame,
                            "time_received": timeStamp,
                            "msg_size": len(rtcmFrame),
                            "mountpoint_id": mountPoint.mountpoint_id,
                        }
                    )
            except (OSError, ConnectionError, IndexError):
                ntripclient = await ntripLogger.requestStream(
                    ntripclient, casterSettings, log_disconnect=True
                )
    except:
        await ntripLogger.closePool()

    # we end here by closing the connection

    ntripclient.ntripWriter.close()
    # Fails on SSL connection and commented out:
    # await ntripclient.ntripWriter.wait_closed()
    while not ntripclient.ntripWriter.is_closing():
        logger.info(f"Waiting for connection to close: {mountPoint.mountpoint}.")
        await asyncio.sleep(0.5)
    logger.info(f"{mountPoint.mountpoint}: Closed connection.")

async def rtcmStreamTasks(
    casterSettingsDict: dict,
    dbSettings: DbSettings,
    mountPointList: list,
    sharedEncoded: list,
    lock,
    pipe_read: Connection
) -> None:
    tasks = {}

    for mountpoint in mountPointList:
        casterSettings = casterSettingsDict[mountpoint.caster]
        tasks[mountpoint.mountpoint] = asyncio.create_task(
            procRtcmStream(
                casterSettings,
                dbSettings,
                mountpoint,
                lock,
                sharedEncoded,
            ),
            name=mountpoint.mountpoint,
        )

    # Create the watchdog task
    tasks["watchdog"] = asyncio.create_task(
        watchdogHandler(casterSettingsDict, mountPointList, tasks, sharedEncoded, lock)
    )

    # We wait until a signal is sent
    while not pipe_read.poll():
        await asyncio.sleep(1)
    logger.debug(f"Reader process on loop {id(asyncio.get_running_loop())} received shutdown signal.")
    global INIT_GRACEFUL_SHUTDOWN
    INIT_GRACEFUL_SHUTDOWN = True
    tasks["watchdog"].cancel()

    # Wait for each task to complete
    await asyncio.gather(*tasks.values())

# def reduceCasterDict(casterSettingsDict: dict, casterStatus: list) -> dict:
#     reducedCasterSettingsDict = {}
#     for caster, status in zip(casterSettingsDict.keys(), casterStatus):
#         if status == 1:
#             reducedCasterSettingsDict[caster] = casterSettingsDict[caster]
#     return reducedCasterSettingsDict
    logger.debug(f"Reader process on loop {id(asyncio.get_running_loop())} done.")



async def downloadSourceTable(
    casterSettingsDict: dict,
    dbSettings: DbSettings,
    sleepTime: int = 10,
    retry: int = 3,
) -> None:
    """
    Reads the sourcetable and inserts relevant metadata for the requested mountpoints into the database.
    """
    # Create an instance of NtripClients
    ntripclient = NtripClients()
    mountpoints = []
    # replaced with CasterSettings attribute active
    # casterStatus = [0] * len(casterSettingsDict)  # Initialize the list with zeros

    for caster, casterSettings in casterSettingsDict.items():
        logger.info(
            f"Requesting source table from caster {caster} for mountpoint information at {casterSettings.casterUrl}."
        )
        sourceTable = None
        fail = 0
        # CBH: This screams for a context manager, a class for source table download and processing
        while True:
            try:
                sourceTable = await ntripclient.requestSourcetable(
                    casterSettings.casterUrl
                )

                logger.info(f"Source table received for caster {caster}.")
                break  # If the source table is successfully received, break the loop
            except Exception as error:
                fail += 1
                sleepTime = 5 * fail
                sleepTime = min(sleepTime, 300)
                logger.error(
                    f"{fail} failed attempt(s) to NTRIP connect to {casterSettings.casterUrl}: {error}. Will retry in {sleepTime} seconds."
                )
                await asyncio.sleep(sleepTime)
                # If fail is greater than retry (default value 3), break the loop
                if (fail > retry):
                    logger.info(
                        f"Attempted to connect to {casterSettings.casterUrl} {retry} times without success. Skipping caster."
                    )
                    break
        if sourceTable:
            async with DatabaseConnection(dbSettings) as connection:
                try:
                    casterId = await connection.fetchval(
                        "SELECT insert_caster($1::json)", json.dumps([caster, casterSettings.casterUrl, casterSettings.user])
                    )
                    casterSettings.casterId = casterId
                    casterSettings.active = True
                    logger.debug(
                        f"Inserted {caster} into the database with id {casterId}. Gathering info on {casterSettings.mountpoints}"
                    )
                except Exception as exc:
                    logger.error(f"Failed to write caster {caster} to database: {exc}. Skipping")
                    continue
                
                try:
                    # collect information from source table
                    for row in sourceTable:
                        sourceCols = row.split(sep=";")
                        if sourceCols[0] == "STR" and sourceCols[1] in casterSettings.sitenames:
                            mountpoint = casterSettings.mountpoints[casterSettings.sitenames.index(sourceCols[1])]

                            mountpoint.identifier = sourceCols[2]
                            mountpoint.format = sourceCols[3]
                            mountpoint.format_details = sourceCols[4]
                            mountpoint.carrier = int(sourceCols[5])
                            mountpoint.nav_system = sourceCols[6]
                            mountpoint.network = sourceCols[7]
                            mountpoint.country = sourceCols[8]
                            mountpoint.latitude = float(sourceCols[9])
                            mountpoint.longitude = float(sourceCols[10])
                            mountpoint.nmea = int(sourceCols[11])
                            mountpoint.solution = int(sourceCols[12])
                            mountpoint.generator = sourceCols[13]
                            mountpoint.compr_encryp = sourceCols[14]
                            mountpoint.authentication = sourceCols[15]  
                            mountpoint.fee = sourceCols[16]
                            mountpoint.bitrate = int(sourceCols[17])
                            mountpoint.misc = sourceCols[18]

                except Exception as exc:
                    logger.error(f"Failed to read source table information {exc}. Continuing without details.")

                try:
                    # prepare list of dictionaries for database insertion of mountpoints
                    json_table = []
                    for mountpoint in casterSettings.mountpoints:
                        mountpoint.caster_id = casterSettings.casterId
                        mountpoint.caster = casterSettings.name

                        json_table.append(
                            mountpoint.as_dict()
                        )
                        
                    mountpointJson = json.dumps(json_table)
                    mountpoint_ids = await connection.fetchval(
                        "SELECT insert_mountpoints($1::json)",
                        mountpointJson,
                    )

                    for mountpoint_id, mountpoint in zip(mountpoint_ids, casterSettings.mountpoints):
                        mountpoint.mountpoint_id = mountpoint_id
                    logger.debug(
                        f"Inserted {len(casterSettings.mountpoints)} mountpoints metadata into the database with ids {mountpoint_ids}."
                    )
                except Exception as exc:
                    logger.error(f"Failed to write mountpoints {casterSettings.mountpoints} to database: {exc}.")
    


def load_connections():
    with open('./conf/connections.json', 'r') as f:
        connections = json.load(f)
    
    casterSettingsDict = {}

    for connection in connections:
        if connection["type"] == "caster":
            caster = Caster()
            caster.name = connection["id"]
            caster.casterUrl = connection["host"] + ":" + str(connection["port"])
            caster.user = connection["auth"]["username"]
            caster.password = connection["auth"]["password"]

            caster.mountpoints = [Mountpoint(mountpoint["name"]) for mountpoint in connection["mountpoints"] if mountpoint["enabled"] == True]

            casterSettingsDict[caster.name] = caster

    return casterSettingsDict




def loadDbSettings():
    dbSettings = DbSettings()
    dbSettings.host = os.getenv("DB_HOST")
    dbSettings.port = int(os.getenv("DB_PORT"))
    dbSettings.database = os.getenv("DB_NAME")
    dbSettings.user = os.getenv("DB_USER")
    dbSettings.password = os.getenv("DB_PASSWORD")
    dbSettings.storeObservations = os.getenv("DB_STORE_OBSERVATIONS") == "True"

    return dbSettings

def loadMultiProcessingSettings():
    processingSettings = MultiprocessingSettings()
    processingSettings.multiprocessingActive = (
        os.getenv("MULTIPROCESSING_ACTIVE") == "True"
    )
    processingSettings.maxReaders = int(os.getenv("MAX_READERS"))
    processingSettings.readersPerDecoder = int(os.getenv("READERS_PER_DECODER"))
    processingSettings.clearCheck = float(
        os.getenv("CLEAR_CHECK")
    )  # Currently un-used. Will be used for clearing shared list.
    processingSettings.appendCheck = float(
        os.getenv("APPEND_CHECK")
    )  # Currently un-used. Will be used for appending shared list.

    return processingSettings

def initializationLogger(
    casterSettingsDict,
    dbSettings: DbSettings,
    processingSettings: MultiprocessingSettings,
):
    logMessages = [
        "----------------------------- Multiprocessing Settings -----------------------------",
        f"Multiprocessing active: {processingSettings.multiprocessingActive}",
    ]

    if processingSettings.multiprocessingActive:
        logMessages.extend(
            [
                "  - Multiprocessing is active. Multi-core setup.",
                f"  - Maximum reading processes: {processingSettings.maxReaders}",
                f"  - Readers per Decoder: {processingSettings.readersPerDecoder}",
                f"  - Database insertion frequency (s): {processingSettings.clearCheck} s (WIP)",
                f"  - Processing Append frequency (s): {processingSettings.appendCheck} s (WIP)",
            ]
        )
    else:
        logMessages.extend(
            [
                "  - Multiprocessing is inactive. Single core setup.",
                "  - Maximum reading processes: Inactive",
                "  - Readers per Decoder: Inactive",
                f"  - Database insertion frequency (s): {processingSettings.clearCheck} s (WIP)",
                f"  - Processing Append frequency (s): {processingSettings.appendCheck} s (WIP)",
            ]
        )

    logMessages.extend(
        [
            "----------------------------- Caster Settings -----------------------------",
            f"Number of casters: {len(casterSettingsDict)}",
        ]
    )

    for i, (caster, settings) in enumerate(casterSettingsDict.items(), start=1):
        logMessages.extend(
            [
                "-------------------------------------",
                f"Caster {i}: {caster}",
                f"Caster URL: {settings.casterUrl}",
                f"Number of mountpoints : {len(settings.mountpoints)}",
            ]
        )

    logMessages.extend(
        [
            "----------------------------- Database Settings -----------------------------",
            f"Database : {dbSettings.database}",
            f"Host & Port : {dbSettings.host}:{dbSettings.port}",
            f"Store observations : {dbSettings.storeObservations}",
        ]
    )

    if dbSettings.storeObservations:
        logMessages.extend(
            [
                "----------------------- NOTE -----------------------",
                "Observables are set to be stored. Expect large data quantities.",
                "Recommended to use less frequent database and list append frequencies.",
            ]
        )
    logMessages.extend(
        [
            "---------------------------------------------------",
            "Initializing the monitor system with above settings.",
        ]
    )
    logger.info("\n".join(logMessages))


class parallelProcess:
    def __init__(self):
        self.pipe_read, self.pipe_write = Pipe(duplex=False)
        self.process = Process(target=self.run)

    def start(self) -> None:
        if self.process.is_alive():
            logger.info(f"Restarting process {self.process.name}, pid {self.process.pid}.")
            self.process.close()

        self.process.start()

    def join(self) -> None:
        self.process.join()

    def close(self) -> None:
        self.process.close()


class readerProcess(parallelProcess):
    def __init__(
        self,
        casterSettingsDict: dict,
        dbSettings: DbSettings,
        mountpointChunk: list,
        sharedEncoded,
        lock: Lock,
    ):
        super().__init__()
        self.casters = casterSettingsDict
        self.database = dbSettings
        self.mountpoints = mountpointChunk
        self.shared = sharedEncoded
        self.lock = lock

    def run(self):
        asyncio.run(
            rtcmStreamTasks(
                self.casters, self.database, self.mountpoints, self.shared, self.lock, self.pipe_read
            )
        )

    def __repr__(self):
        return f"Reader ({self.process.name}, pid {self.process.pid}) with shared memory {hex(id(self.shared))} of mountpoints {[x.mountpoint for x in self.mountpoints]}"


class decoderProcess(parallelProcess):
    def __init__(self, dbSettings: DbSettings, sharedEncoded, lock: Lock):
        super().__init__()
        self.database = dbSettings
        self.shared = sharedEncoded
        self.lock = lock

    def run(self):
        asyncio.run(decodeInsertConsumer(self.shared, self.database, self.lock, self.pipe_read))

    def __repr__(self):
        return f"Decoder ({self.process.name}, pid {self.process.pid}) with shared memory {hex(id(self.shared))}"

async def processWatcher(processes: list[parallelProcess]) -> None:
    """
    Checks threads periodically for crashes
    """
    logger.info(f"Introducing watcher for {processes}")
    while True:
        # Wait 300 seconds between checking processes for aliveness
        await asyncio.sleep(300)

        for proc in processes:
            exitcode = proc.process.exitcode
            logger.debug(
                f"Checking process {proc} {proc.process} which has exit_code {exitcode}."
            )
            if exitcode is not None:
                logger.warning(
                    f"Restarting process {proc} {proc.process} with un-expected exit_code {exitcode}."
                )
                proc.start()


def RunMultiProcessing(
    casterSettingsDict: dict,
    dbSettings: DbSettings,
    processingSettings: MultiprocessingSettings,
):
    mountpointChunks = mountpointSplitter(
        casterSettingsDict, processingSettings.maxReaders
    )
    logger.info(f"Mountpoint chunks: {[[x.mountpoint for x in liste] for liste in mountpointChunks]}")
    numberReaders = min(processingSettings.maxReaders, len(mountpointChunks))
    numberDecoders = math.ceil(numberReaders // processingSettings.readersPerDecoder)

    logger.info(f"Starting {numberReaders} readers and {numberDecoders} decoders.")
    with Manager() as manager:
        sharedEncodedList = [manager.list() for _ in range(numberDecoders)]
        lockList = [Lock() for _ in range(numberDecoders)]
        readingProcesses = []
        for i, mountpointChunk in enumerate(mountpointChunks):
            sharedEncoded = sharedEncodedList[i // processingSettings.readersPerDecoder]
            lock = lockList[i // processingSettings.readersPerDecoder]
            readingProcess = readerProcess(
                casterSettingsDict,
                dbSettings,
                mountpointChunk,
                sharedEncoded,
                lock,
            )
            logger.info(
                f"Starting {readingProcess}."
            )
            readingProcesses.append(readingProcess)

        decoderProcesses = []
        for sharedEncoded, lock in zip(sharedEncodedList, lockList):
            logger.info(hex(id(sharedEncoded)))
            decodingProcess = decoderProcess(dbSettings, sharedEncoded, lock)
            logger.info(
                f"Starting {decodingProcess}."
            )
            decoderProcesses.append(decodingProcess)

        for readingProcess in readingProcesses:
            readingProcess.start()
        for decodingProcess in decoderProcesses:
            decodingProcess.start()

        # here we introduce a watcher of the spawned child processes
        # logger.info(f"Introducing watcher for {readingProcesses + decoderProcesses}")

        # while True:
        #     # Wait 300 seconds between checking processes for aliveness
        #     # This code is blocking, since all work has been distributed on separate processes.
        #     sleep(300)

        #     for proc in readingProcesses + decoderProcesses:
        #         exitcode = proc.process.exitcode
        #         logger.debug(
        #             f"Checking process {proc} {proc.process} which has exit_code {exitcode}."
        #         )
        #         if exitcode is not None:
        #             logger.warning(
        #                 f"Restarting process {proc} {proc.process} with un-expected exit_code {exitcode}."
        #             )
        #             proc.start()
        
        # here we set up a main asyncio loop, which takes care of signal handling and passing on 
        loop = asyncio.new_event_loop()
        signal_handler = SignalHandler(loop, readingProcesses + decoderProcesses)
        # we run forever until the process is interrupted/killed from OS
        loop.run_forever()
        logger.debug(f"Main asyncio loop {id(loop)} ended. Joining processes.")

        for readingProcess in readingProcesses:
            readingProcess.join()
        for decodingProcess in decoderProcesses:
            decodingProcess.join()

        logger.info("Goodbye!")



def main(
    casterSettingsDict: dict,
    dbSettings: DbSettings,
    processingSettings: MultiprocessingSettings,
):
    """
    The main function that sets up signal handlers and starts the RTCM stream tasks.

    Parameters contain information in the form of dataclasses instances created from the .env configuration:
    casterSettingsDict (CasterSettingsDict): A dictionary of Caster instances containing the caster settings.
    dbSettings (DbSettings): An instance of DbSettings containing the database connection details.
    processingSettings (MultiprocessingSettings): An instance of MultiprocessingSettings containing settings.
    """

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # cannot continue until database connection is established
    loop.run_until_complete(DatabaseHandler.waitDbConnection(dbSettings))

    initializationLogger(
        casterSettingsDict, dbSettings, processingSettings
    )  # Setup statistics

    # Download the source table from casters.
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(
            downloadSourceTable(casterSettingsDict, dbSettings)
        )
    except Exception as error:
        logger.error(
            f"Failed to retrieve source tables: {error}.")


    # reduce caster dictionary to contain only active casters
    # casterSettingsDict = reduceCasterDict(casterSettingsDict, casterStatus)

    casterSettingsDict = {key: caster for key, caster in casterSettingsDict.items() if caster.active}
    logger.debug(casterSettingsDict)

    # Always run multiprocessing
    RunMultiProcessing(casterSettingsDict, dbSettings, processingSettings)



# This code is only executed if the script is run directly
if __name__ == "__main__":
    # Set up argument parser
    parser = ArgumentParser()
    # Add command line arguments
    parser.add_argument(
        "-t",
        "--test",
        action="store_true",
        help="Test connection to Ntripcaster without committing data to database.",
    )
    parser.add_argument(
        "-1",
        "--ntrip1",
        action="store_true",
        help="Use Ntrip 1 protocol.",
    )
    parser.add_argument(
        "-l",
        "--logfile",
        action="store",
        help="Log to file. Default output is terminal.",
    )
    parser.add_argument(
        "-v",
        "--verbosity",
        action="count",
        default=0,
        help="Increase verbosity level.",
    )
    # Parse command line arguments
    args = parser.parse_args()

    # Set verbosity level
    args.verbosity = 2
    # Set logging level based on verbosity
    logLevel = logging.ERROR
    if args.verbosity == 1:
        logLevel = logging.WARNING
    elif args.verbosity == 2:
        logLevel = logging.INFO
    elif args.verbosity > 2:
        logLevel = logging.DEBUG
    # Set up logging
    logformat = "%(asctime)s:%(name)s:%(levelname)s:%(message)s"
    if args.logfile:
        logging.basicConfig(
            level=logLevel,
            filename=args.logfile,
            format=logformat,
        )
    else:
        logging.basicConfig(
            level=logLevel, format=logformat
        )

    load_dotenv()
    # casterSettingsDict contains the Caster instances (dataclass) for all casters
    casterSettingsDict = load_connections()

    # dataclass for database settings
    dbSettings = loadDbSettings()

    multiProcessingSettings = loadMultiProcessingSettings()

    # If test mode is enabled, don't use database settings
    if args.test:
        dbSettings = None
    # Run the main function with the specified settings
    main(casterSettingsDict, dbSettings, multiProcessingSettings)

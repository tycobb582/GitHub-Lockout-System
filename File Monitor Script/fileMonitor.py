import subprocess
import time
from discord import Webhook
import aiohttp
import asyncio
from googleapiclient.discovery import build
from dotenv import load_dotenv
import os
import sys
from FileInfo import FileInfo
from google.oauth2 import service_account


workingDirectory = os.getcwd()
dotenv_path = os.path.join(workingDirectory, ".env")
load_dotenv(dotenv_path=dotenv_path)

REPO_PATH = workingDirectory
USER_NAME = os.environ.get("USER_NAME")
USER_ID = os.environ.get("USER_ID")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
SHEETS_API_KEY = os.environ.get("SHEETS_API_KEY")
SHEET_ID = os.environ.get("SHEET_ID")
DISCORD_AUTH = os.environ.get("DISCORD_AUTH")
GUILD_ID = os.environ.get("GUILD_ID")
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
# You can download your service account's JSON from the Credentials tab in Google Cloud's APIs & Services section
SERVICE_ACCOUNT_FILE = 'service_account.json'

credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
command = ['git', '-C', REPO_PATH, 'diff', '--name-only']
sheets = build('sheets', 'v4', developerKey=SHEETS_API_KEY, credentials=credentials).spreadsheets()

fileCache = {}  # Maps file name to FileInfo
recentWarnings = []


async def scanSheet(modifiedFiles: list, webhook: Webhook):
    """
    A one-time scan of all files in the lockout sheet. Caches the status of each file for fast checks later.
    :param modifiedFiles: The list of files currently modified locally.
    :param webhook: A reference to the channel webhook.
    """
    print("Beginning scan of lockout sheet...")
    result = sheets.values().get(spreadsheetId=SHEET_ID, range="Sheet1").execute()
    values = result.get('values', [])
    botRescan = False
    for i in range(1, len(values)):
        data = values[i]
        fileName = data[0]
        if data[1] == "Yes":
            fileCache[fileName] = FileInfo(True, data[2], i+1)
            if fileName not in modifiedFiles and data[2] == USER_NAME:
                print(f"{fileName} is locked and no longer modified locally. Freeing now...")
                body = {"values": [["No", ""]]}
                sheets.values().update(spreadsheetId=SHEET_ID,
                                       range=f"Sheet1!B{i+1}:C{i+1}",
                                       valueInputOption="USER_ENTERED", body=body).execute()
                fileCache[fileName].locked = False
                fileCache[fileName].lockedBy = None
                webhookNotify = await webhook.send(content=f"NOTIFY RESCAN", username="Tyler Jr.", wait=True)
                time.sleep(2)
                await webhook.delete_message(webhookNotify.id)
            continue
        # If file is free, and we have been warned about the file, remove the fileName from remembered warnings.
        elif fileName in recentWarnings:
            recentWarnings.remove(fileName)
        fileCache[fileName] = FileInfo(False, None, i+1)
    print("Scan complete")


async def checkAndAct(fileName: str, webhook: Webhook):
    """
    Checks whether a modified file is locked out and responds appropriately. Unlocked files are automatically locked for
    the user, and the user is warned about modifying a locked file.
    :param fileName: The name of the file to check.
    :param webhook: A reference to the Webhook used to warn users.
    """
    try:
        status = fileCache[fileName]
    except KeyError:
        print(f"{fileName} not found in lockout sheet.")
        print(fileCache)
        return
    if status.locked:
        if status.lockedBy != USER_NAME:
            if fileName not in recentWarnings:
                print(f"{fileName} is locked out by {status.lockedBy}. Sending warning...")
                await lockoutWarning(fileName, status.lockedBy, webhook)
                recentWarnings.append(fileName)
            else:
                print(f"{fileName} is locked out by another user ({status.lockedBy}). Warning has been sent.")
        else:
            print(f"You currently have {fileName} locked out.")
    else:
        print(f"{fileName} is modified and free. Marking file as locked for {USER_NAME}.")
        body = {"values": [["Yes", USER_NAME]]}
        sheets.values().update(spreadsheetId=SHEET_ID, range=f"Sheet1!B{status.sheetRow}:C{status.sheetRow}", valueInputOption="USER_ENTERED", body=body).execute()
        webhookNotify = await webhook.send(content=f"NOTIFY RESCAN", username="Tyler Jr.", wait=True)
        time.sleep(1)
        await webhook.delete_message(webhookNotify.id)

        return


async def lockoutWarning(lockedFile: str, lockedOutBy: str, webhook: Webhook):
    """
    Warns user of modifying locked files using a Discord webhook.
    :param lockedFile: The name of the locked file.
    :param lockedOutBy: The name of the user who has locked this file out.
    :param webhook: The webhook connected to the user's Discord server.
    :return:
    """
    await webhook.send(content=f"<@{USER_ID}>, {lockedFile} is currently locked out by {lockedOutBy} and modified on your machine. If you must modify this file, speak to them to unblock yourself or update the Lockout Sheet if it is incorrect. Be sure to pull before pushing this file.", username="Tyler Jr.")


async def monitorFiles():
    """
    Connects to discord server using a webhook. Performs one loop every minute wherein the lockout sheet is scanned for
    the status of every file, then each modified file is checked against the stored status to determine if a warning
    should be issued.
    """
    async with aiohttp.ClientSession() as session:
        partialWebhook = Webhook.from_url(WEBHOOK_URL, session=session)
        partialWebhook.auth_token = DISCORD_AUTH
        webhook = await partialWebhook.fetch()
        print(webhook.type)
        try:
            while True:
                # First, get list of modified files
                modifiedFiles = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                        text=True)
                modifiedFilesRaw = modifiedFiles.stdout.split("\n")
                modifiedFiles = []    # Stores name of every currently modified asset file
                for file in modifiedFilesRaw:
                    if file.find(".uasset") >= 0 or file.find(".umap") >= 0 and file.find("External") == -1:
                        startIndex = file.rfind("/") + 1
                        fileName = file[startIndex::]
                        modifiedFiles.append(fileName)
                # Scan and cache the status of project files, release locks on files that are not currently modified
                await scanSheet(modifiedFiles, webhook)
                for file in modifiedFiles:
                        print("Modified: " + file + ". Verifying lock...")
                        await checkAndAct(file, webhook)
                print()
                time.sleep(20)
        except KeyboardInterrupt:
            print("Program halted.")


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(monitorFiles())
    loop.close()


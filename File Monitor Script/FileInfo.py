class FileInfo:
    def __init__(self, locked, lockedBy, sheetRow):
        self.locked = locked
        self.lockedBy = lockedBy
        self.sheetRow = sheetRow

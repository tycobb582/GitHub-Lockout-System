let files = [];
var AUTH_TOKEN = "INSERT AUTH HERE";  // NEEDS EDITED

function myFunction() 
{
  scanFolder("Content");
  var app = SpreadsheetApp;
  var lockoutSpread = app.openByUrl("LINK TO YOUR SPREADSHEET");  // NEEDS EDITED
  var lockoutSheet = lockoutSpread.getSheetByName("Sheet1");
  files.sort();
  for (i = 2; i < files.length + 2; i++)
  {
    var fileName = files[i-2];
    var newValues = [fileName]
    var currentIndexOfFile = binarySearchForFile(files, fileName);
    var rowRange = lockoutSheet.getRange(currentIndexOfFile + 2, 1, 1, 3);
    var values = rowRange.getValues()[0];
    if (currentIndexOfFile == -1) // New file introduced to the system
    {
        newValues.push("No");
        newValues.push("");
    }
    else
    {
      newValues.push(values[1]);
      newValues.push(values[2]);
    }
    rowRange.setValues([newValues]);
  }
}

function scanFolder(path)
{
  const GIT_API_URL = `https://api.github.com/repos/REPO_OWNER_NAME/REPO_NAME/contents/$(path)?ref=main`; // NEEDS EDITED

  var urlFetchOptions = 
  {
    "method": "GET",
    "headers": 
    {
      "Accept": "application/vnd.github.v+-3+json",
      "Content-Type": "application/json",
      "Authorization": `Bearer ${AUTH_TOKEN}`
    }
  };
  var gitResponse = UrlFetchApp.fetch(GIT_API_URL, urlFetchOptions);
  var parsedResponse = JSON.parse(gitResponse);
  for (i in parsedResponse)
  {
    var item = parsedResponse[i];
    var itemName = item["name"];
    if (itemName.includes("."))
    {
      if (itemName.includes(".uasset") || itemName.includes(".umap"))
      {
        files.push(itemName);
      }
    }
    else
    {
      var newPath = path.concat(`/${itemName}`);
      if (!newPath.includes("External"))
      {
        scanFolder(newPath);
      }
    }
  }
}

function binarySearchForFile(files, query)
{
    lowIndex = 0;
    highIndex = files.length - 1;
    while (lowIndex <= highIndex) 
    {
        var midpoint = lowIndex + (highIndex - lowIndex) // 2;

        // Check if query is present at mid
        if (files[midpoint] == query)
            return midpoint;

        // If query is greater greater alphabetically, ignore left half
        if (alphabeticalSortCheck(query, files[midpoint]) == 1)
            lowIndex = midpoint + 1;

        // If query is lower alphabetically, ignore right half
        else
            highIndex = midpoint - 1;
    }

    // If we reach here, then element was not present
    return -1;
}

function alphabeticalSortCheck(stringToCheck, stringToCheckAgainst)
{
  var stagingArray = [stringToCheck, stringToCheckAgainst];
  stagingArray.sort();
  if (stagingArray[0] == stringToCheck)
    return -1;
  return 1;
}

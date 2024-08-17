let files = [];
var AUTH_TOKEN = "INSERT AUTH HERE";

function myFunction() 
{
  scanFolder("Content");
  var app = SpreadsheetApp;
  var lockoutSpread = app.openByUrl("LINK TO YOUR SPREADSHEET");
  var lockoutSheet = lockoutSpread.getSheetByName("Sheet1");
  files.sort();
  for (i = 2; i < files.length; i++)
  {
    var rowRange = lockoutSheet.getRange(i, 1, 1, 3);
    var values = rowRange.getValues()[0];
    Logger.log(values);
    var newValues = [files[i-2]]
    if (values[2] == "")
      newValues.push("No");
    else
      newValues.push[values[1]];
    newValues.push(values[2]);
    Logger.log(newValues);
    rowRange.setValues([newValues]);
  }
}

function scanFolder(path)
{
  //Logger.log(path);
  const GIT_API_URL = `API LINK TO YOUR REPO`;

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

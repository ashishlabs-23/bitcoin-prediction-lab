/**
 * ==============================================================================
 * BTCognitive — AI Experiment Arena Google Sheets Sync Webhook
 * ==============================================================================
 * 
 * INSTRUCTIONS:
 * 1. Open Google Sheets (https://sheets.new)
 * 2. Click "Extensions" -> "Apps Script"
 * 3. Delete any code in the editor, paste this entire script, and save (Ctrl+S).
 * 4. Click "Deploy" -> "New deployment"
 * 5. Select type: "Web app"
 * 6. Set:
 *    - Description: "BTCognitive Arena Sync"
 *    - Execute as: "Me"
 *    - Who has access: "Anyone"
 * 7. Click "Deploy", authorize permissions, and COPY the Web App URL!
 * 8. Paste your Web App URL into the BTCognitive AI Experiment Arena sync input or call:
 *    POST http://127.0.0.1:8000/api/arena/sync_google_sheet with {"webhook_url": "YOUR_URL"}
 * ==============================================================================
 */

function doPost(e) {
  try {
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    var contents = JSON.parse(e.postData.contents);
    var trades = contents.trades || [];
    
    // Check if headers exist; if not, initialize headers
    if (sheet.getLastRow() === 0) {
      sheet.appendRow([
        "Trade ID",
        "Timestamp (UTC)",
        "Action",
        "Confidence",
        "Entry Price ($)",
        "Exit Price ($)",
        "Quantity (BTC)",
        "PnL ($)",
        "Balance After ($)",
        "RSI",
        "MACD",
        "EMA 20",
        "EMA 50",
        "Volume",
        "Model Version",
        "Reasoning"
      ]);
      
      // Format Header Row (Dark Cyberpunk / Institutional Theme)
      var headerRange = sheet.getRange(1, 1, 1, 16);
      headerRange.setBackground("#0A101E");
      headerRange.setFontColor("#00E5A8");
      headerRange.setFontWeight("bold");
      sheet.setFrozenRows(1);
    }
    
    // Get existing Trade IDs to avoid duplicate rows
    var existingIds = {};
    if (sheet.getLastRow() > 1) {
      var idValues = sheet.getRange(2, 1, sheet.getLastRow() - 1, 1).getValues();
      for (var i = 0; i < idValues.length; i++) {
        existingIds[idValues[i][0]] = true;
      }
    }
    
    var rowsToAppend = [];
    for (var j = 0; j < trades.length; j++) {
      var t = trades[j];
      if (!existingIds[t.id]) {
        rowsToAppend.push([
          t.id,
          t.timestamp,
          t.action,
          t.confidence,
          t.entry_price,
          t.exit_price,
          t.quantity,
          t.pnl,
          t.balance_after,
          t.rsi || "",
          t.macd || "",
          t.ema20 || "",
          t.ema50 || "",
          t.volume || "",
          t.model_version || "Genome v4.1",
          t.reasoning || ""
        ]);
      }
    }
    
    if (rowsToAppend.length > 0) {
      var startRow = sheet.getLastRow() + 1;
      sheet.getRange(startRow, 1, rowsToAppend.length, 16).setValues(rowsToAppend);
      
      // Apply Conditional formatting for PnL column (Col 8)
      for (var r = 0; r < rowsToAppend.length; r++) {
        var pnlCell = sheet.getRange(startRow + r, 8);
        var pnlVal = rowsToAppend[r][7];
        if (pnlVal > 0) {
          pnlCell.setFontColor("#00E5A8");
        } else if (pnlVal < 0) {
          pnlCell.setFontColor("#FF5C7C");
        }
      }
    }
    
    return ContentService.createTextOutput(JSON.stringify({
      status: "success",
      rows_added: rowsToAppend.length,
      total_trades_in_sheet: sheet.getLastRow() - 1
    })).setMimeType(ContentService.MimeType.JSON);
    
  } catch (error) {
    return ContentService.createTextOutput(JSON.stringify({
      status: "error",
      message: error.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  }
}

function doGet(e) {
  return ContentService.createTextOutput(JSON.stringify({
    status: "online",
    message: "BTCognitive AI Experiment Arena Google Apps Script Webhook is active and listening for POST payloads."
  })).setMimeType(ContentService.MimeType.JSON);
}

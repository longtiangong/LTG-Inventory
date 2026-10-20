const SPREADSHEET_ID = "1yDjGjaJXyhEH_k-bijrdl_8wXP4zot6SFloW16Bx27A";
const WORKSHEET_NAME = "龍天宮庫存系統";
const INVENTORY_COLUMNS = [
  "項目",
  "上一次月份",
  "上一次月份總庫存量",
  "進貨日期",
  "進貨數量",
  "使用日期",
  "使用項目",
  "使用數量",
  "盤點日期",
  "盤點數量",
  "結果",
  "總庫存量",
  "供應商名稱",
  "電話",
  "聯絡人",
  "安全庫存量",
];
const LEGACY_INVENTORY_COLUMNS = INVENTORY_COLUMNS.slice(0, -1);
const ARCHIVE_COLUMNS = [...INVENTORY_COLUMNS, "刪除時間", "刪除批次ID"];

function jsonResponse(body) {
  return ContentService.createTextOutput(JSON.stringify(body)).setMimeType(
    ContentService.MimeType.JSON,
  );
}

function constantTimeEquals(left, right) {
  if (left.length !== right.length) return false;
  let difference = 0;
  for (let index = 0; index < left.length; index += 1) {
    difference |= left.charCodeAt(index) ^ right.charCodeAt(index);
  }
  return difference === 0;
}

function literalCellValue(value) {
  if (typeof value === "string" && /^[=+\-@]/.test(value)) {
    return `'${value}`;
  }
  return value;
}

function doPost(event) {
  try {
    const request = JSON.parse(event.postData.contents);
    const configuredToken = PropertiesService.getScriptProperties().getProperty(
      "ARCHIVE_TOKEN",
    );
    if (
      !configuredToken ||
      typeof request.token !== "string" ||
      !constantTimeEquals(request.token, configuredToken)
    ) {
      return jsonResponse({ success: false, error: "Invalid token" });
    }
    if (
      request.action !== "archive_delete" ||
      !Array.isArray(request.columns) ||
      JSON.stringify(request.columns) !== JSON.stringify(INVENTORY_COLUMNS) ||
      !Array.isArray(request.rows) ||
      request.rows.length === 0 ||
      request.rows.some(
        (row) => !Array.isArray(row) || row.length !== INVENTORY_COLUMNS.length,
      ) ||
      typeof request.deletion_id !== "string" ||
      !request.deletion_id ||
      typeof request.deleted_at !== "string"
    ) {
      return jsonResponse({ success: false, error: "Invalid archive payload" });
    }

    const lock = LockService.getScriptLock();
    lock.waitLock(30000);
    try {
      const spreadsheet = SpreadsheetApp.openById(SPREADSHEET_ID);
      const sheet = spreadsheet.getSheetByName(WORKSHEET_NAME);
      if (!sheet) throw new Error(`Worksheet not found: ${WORKSHEET_NAME}`);

      if (sheet.getLastRow() === 0) {
        sheet.getRange(1, 1, 1, ARCHIVE_COLUMNS.length).setValues([
          ARCHIVE_COLUMNS,
        ]);
      } else {
        const header = sheet
          .getRange(1, 1, 1, ARCHIVE_COLUMNS.length)
          .getDisplayValues()[0];
        if (header.every((value) => value === "")) {
          sheet.getRange(1, 1, 1, ARCHIVE_COLUMNS.length).setValues([
            ARCHIVE_COLUMNS,
          ]);
        } else if (
          JSON.stringify(header.slice(0, LEGACY_INVENTORY_COLUMNS.length)) ===
            JSON.stringify(LEGACY_INVENTORY_COLUMNS) &&
          header[LEGACY_INVENTORY_COLUMNS.length] === "刪除時間" &&
          header[LEGACY_INVENTORY_COLUMNS.length + 1] === "刪除批次ID"
        ) {
          sheet.insertColumnAfter(LEGACY_INVENTORY_COLUMNS.length);
          sheet.getRange(1, 1, 1, ARCHIVE_COLUMNS.length).setValues([
            ARCHIVE_COLUMNS,
          ]);
        } else if (
          JSON.stringify(header.slice(0, LEGACY_INVENTORY_COLUMNS.length)) ===
            JSON.stringify(LEGACY_INVENTORY_COLUMNS) &&
          header
            .slice(LEGACY_INVENTORY_COLUMNS.length)
            .every((value) => value === "")
        ) {
          sheet.insertColumnAfter(LEGACY_INVENTORY_COLUMNS.length);
          sheet.getRange(1, 1, 1, ARCHIVE_COLUMNS.length).setValues([
            ARCHIVE_COLUMNS,
          ]);
        } else if (
          JSON.stringify(header.slice(0, INVENTORY_COLUMNS.length)) ===
            JSON.stringify(INVENTORY_COLUMNS) &&
          header[INVENTORY_COLUMNS.length] === "" &&
          header[INVENTORY_COLUMNS.length + 1] === ""
        ) {
          sheet
            .getRange(1, INVENTORY_COLUMNS.length + 1, 1, 2)
            .setValues([["刪除時間", "刪除批次ID"]]);
        } else if (JSON.stringify(header) !== JSON.stringify(ARCHIVE_COLUMNS)) {
          throw new Error("Worksheet header does not match the archive columns");
        }
      }

      const lastRow = sheet.getLastRow();
      if (lastRow > 1) {
        const deletionIds = sheet
          .getRange(2, ARCHIVE_COLUMNS.length, lastRow - 1, 1)
          .getDisplayValues()
          .flat();
        if (deletionIds.includes(request.deletion_id)) {
          return jsonResponse({ success: true, duplicate: true });
        }
      }

      const archivedRows = request.rows.map((row) =>
        row.map(literalCellValue).concat([
          request.deleted_at,
          request.deletion_id,
        ]),
      );
      sheet
        .getRange(lastRow + 1, 1, archivedRows.length, ARCHIVE_COLUMNS.length)
        .setValues(archivedRows);

      return jsonResponse({ success: true, duplicate: false });
    } finally {
      lock.releaseLock();
    }
  } catch (error) {
    return jsonResponse({ success: false, error: String(error.message || error) });
  }
}

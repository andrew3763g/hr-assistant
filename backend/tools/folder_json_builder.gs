/** ========== CONFIG ========== */
const ROOT_FOLDER_ID = "1nxEe7wv8mYLbwuyu_4-pgjAXQN-1fSit";
const MAX_DEPTH = 20; // защиту от бесконечной вложенности оставим большой

/** ========== MAIN ========== */
function exportJson() {
  const root = DriveApp.getFolderById(ROOT_FOLDER_ID);
  const snapshot = buildFolderSnapshot(root, 0);

  const json = JSON.stringify(snapshot, null, 2);
  const blob = Utilities.newBlob(
    json,
    "application/json",
    `drive_snapshot_${new Date().toISOString().slice(0, 10)}.json`
  );
  // Сохраняем JSON прямо в эту же папку
  root.createFile(blob);

  Logger.log("Saved snapshot JSON in folder: %s", root.getName());
}

/** ========== HELPERS ========== */
function buildFolderSnapshot(folder, depth) {
  if (depth > MAX_DEPTH) {
    return {
      folder_name: folder.getName(),
      folder_id: folder.getId(),
      note: "depth limit reached",
      total_file_count: 0,
      files_reviewed_count: 0,
      contents: [],
    };
  }

  const out = {
    folder_name: folder.getName(),
    folder_id: folder.getId(),
    total_file_count: 0,
    files_reviewed_count: 0,
    contents: [],
  };

  // ФАЙЛЫ
  const files = folder.getFiles();
  while (files.hasNext()) {
    const f = files.next();
    const created = f.getDateCreated ? f.getDateCreated() : null;
    const updated = f.getLastUpdated ? f.getLastUpdated() : null;

    out.contents.push({
      type: "file",
      title: f.getName(),
      file_chip_id: `[${escapeMd(
        f.getName()
      )}](https://drive.google.com/open?id=${f.getId()})`,
      id: f.getId(),
      mime_type: f.getMimeType(),
      created_time: created ? created.toISOString() : null,
      modified_time: updated ? updated.toISOString() : null,
    });
    out.total_file_count++;
    out.files_reviewed_count++;
  }

  // ПАПКИ (рекурсивно)
  const subfolders = folder.getFolders();
  while (subfolders.hasNext()) {
    const sf = subfolders.next();
    const sub = buildFolderSnapshot(sf, depth + 1);

    // Отдельная запись о папке + её содержимое
    out.contents.push({
      type: "folder",
      title: sf.getName(),
      folder_id: sf.getId(),
      file_chip_id: `[${escapeMd(
        sf.getName()
      )}](https://drive.google.com/drive/folders/${sf.getId()})`,
      id: sf.getId(),
      summary: {
        total_file_count: sub.total_file_count,
        files_reviewed_count: sub.files_reviewed_count,
      },
      contents: sub.contents,
    });

    out.total_file_count += sub.total_file_count;
    out.files_reviewed_count += sub.files_reviewed_count;
  }

  return out;
}

function escapeMd(s) {
  // на всякий случай экранируем скобки/квадратные скобки, чтобы markdown-ссылка не ломалась
  return String(s).replace(/([\[\]\(\)])/g, "\\$1");
}

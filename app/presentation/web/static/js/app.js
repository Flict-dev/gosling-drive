const tokenKey = "gosling_drive_token";
const authPanel = document.querySelector("#authPanel");
const drivePanel = document.querySelector("#drivePanel");
const logoutButton = document.querySelector("#logoutButton");
const toast = document.querySelector("#toast");
const progressBar = document.querySelector("#progressBar");
const uploadStatus = document.querySelector("#uploadStatus");
const fileList = document.querySelector("#fileList");

function getToken() {
  return localStorage.getItem(tokenKey);
}

function setToken(token) {
  localStorage.setItem(tokenKey, token);
}

function clearToken() {
  localStorage.removeItem(tokenKey);
}

function showToast(message) {
  toast.textContent = message;
  toast.classList.remove("hidden");
  window.setTimeout(() => toast.classList.add("hidden"), 3600);
}

async function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const token = getToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  const response = await fetch(`/api${path}`, { ...options, headers });
  const text = await response.text();
  const payload = text ? JSON.parse(text) : null;
  if (!response.ok) {
    throw new Error(payload?.detail || "Request failed");
  }
  return payload;
}

function updateMode() {
  const hasToken = Boolean(getToken());
  authPanel.classList.toggle("hidden", hasToken);
  drivePanel.classList.toggle("hidden", !hasToken);
  logoutButton.classList.toggle("hidden", !hasToken);
  if (hasToken) {
    loadFiles();
  }
}

document.querySelector("#loginForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  try {
    const payload = await api("/auth/login", {
      method: "POST",
      body: JSON.stringify(Object.fromEntries(form)),
    });
    setToken(payload.access_token);
    event.currentTarget.reset();
    updateMode();
    showToast("Вход выполнен");
  } catch (error) {
    showToast(error.message);
  }
});

document.querySelector("#registerForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  try {
    await api("/auth/register", {
      method: "POST",
      body: JSON.stringify(Object.fromEntries(form)),
    });
    event.currentTarget.reset();
    showToast("Аккаунт создан");
  } catch (error) {
    showToast(error.message);
  }
});

logoutButton.addEventListener("click", () => {
  clearToken();
  updateMode();
});

document.querySelector("#folderForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  try {
    await api("/folders/", {
      method: "POST",
      body: JSON.stringify(Object.fromEntries(form)),
    });
    event.currentTarget.reset();
    showToast("Папка создана");
  } catch (error) {
    showToast(error.message);
  }
});

document.querySelector("#refreshButton").addEventListener("click", loadFiles);

document.querySelector("#uploadForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const input = document.querySelector("#fileInput");
  const file = input.files[0];
  if (!file) {
    return;
  }
  try {
    await uploadLargeFile(file);
    event.currentTarget.reset();
    await loadFiles();
    showToast("Файл загружен");
  } catch (error) {
    showToast(error.message);
    uploadStatus.textContent = error.message;
  }
});

async function uploadLargeFile(file, options = {}) {
  progressBar.style.width = "0%";
  uploadStatus.textContent = "Создание сессии загрузки...";

  const initiateBody = {
    size_bytes: file.size,
    content_type: file.type || "application/octet-stream",
  };
  if (!options.omitFilename) {
    initiateBody.filename = file.name;
  }

  const session = await api(options.initiatePath || "/uploads/initiate", {
    method: "POST",
    body: JSON.stringify(initiateBody),
  });

  const completedParts = [];
  let uploadedBytes = 0;
  let nextPart = 1;
  const workers = Array.from({ length: Math.min(4, session.total_parts) }, async () => {
    while (nextPart <= session.total_parts) {
      const partNumber = nextPart;
      nextPart += 1;
      const start = (partNumber - 1) * session.part_size;
      const end = Math.min(start + session.part_size, file.size);
      const blob = file.slice(start, end);
      const urlPayload = await api(`/uploads/${session.upload_session_id}/parts`, {
        method: "POST",
        body: JSON.stringify({ part_numbers: [partNumber] }),
      });
      const response = await fetch(urlPayload.urls[0].url, { method: "PUT", body: blob });
      if (!response.ok) {
        throw new Error(`Не удалось загрузить часть ${partNumber}`);
      }
      const etag = response.headers.get("ETag");
      if (!etag) {
        throw new Error(`MinIO не вернул ETag для части ${partNumber}`);
      }
      completedParts.push({ part_number: partNumber, etag });
      uploadedBytes += blob.size;
      const percent = Math.round((uploadedBytes / file.size) * 100);
      progressBar.style.width = `${percent}%`;
      uploadStatus.textContent = `${percent}%`;
    }
  });

  await Promise.all(workers);
  uploadStatus.textContent = "Завершение загрузки...";
  await api(`/uploads/${session.upload_session_id}/complete`, {
    method: "POST",
    body: JSON.stringify({ parts: completedParts }),
  });
  progressBar.style.width = "100%";
  uploadStatus.textContent = "Готово";
}

async function loadFiles() {
  try {
    const files = await api("/files/");
    fileList.innerHTML = "";
    if (files.length === 0) {
      fileList.innerHTML = '<p class="status">Файлов пока нет</p>';
      return;
    }
    for (const file of files) {
      const row = document.createElement("div");
      row.className = "fileRow";
      row.innerHTML = `
        <div>
          <div class="fileName"></div>
          <div class="fileMeta">${formatSize(file.size_bytes)} · v${file.current_version_number} · ${file.status}</div>
        </div>
        <button class="ghost download">Скачать</button>
        <button class="ghost share">Ссылка</button>
        <button class="ghost version">Новая версия</button>
        <input class="versionInput hidden" type="file">
      `;
      row.querySelector(".fileName").textContent = file.name;
      row.querySelector(".download").addEventListener("click", () => downloadFile(file.id));
      row.querySelector(".share").addEventListener("click", () => createShare(file.id));
      const versionInput = row.querySelector(".versionInput");
      row.querySelector(".version").addEventListener("click", () => versionInput.click());
      versionInput.addEventListener("change", async () => {
        const versionFile = versionInput.files[0];
        if (!versionFile) {
          return;
        }
        try {
          await uploadLargeFile(versionFile, {
            initiatePath: `/files/${file.id}/versions/uploads`,
            omitFilename: true,
          });
          await loadFiles();
          showToast("Новая версия загружена");
        } catch (error) {
          showToast(error.message);
          uploadStatus.textContent = error.message;
        } finally {
          versionInput.value = "";
        }
      });
      fileList.appendChild(row);
    }
  } catch (error) {
    showToast(error.message);
  }
}

async function downloadFile(fileId) {
  try {
    const payload = await api(`/files/${fileId}/download-url`);
    window.location.href = payload.url;
  } catch (error) {
    showToast(error.message);
  }
}

async function createShare(fileId) {
  try {
    const payload = await api("/shares/", {
      method: "POST",
      body: JSON.stringify({ file_id: fileId }),
    });
    const url = `${window.location.origin}/share/${payload.token}`;
    await navigator.clipboard.writeText(url);
    showToast("Публичная ссылка скопирована");
  } catch (error) {
    showToast(error.message);
  }
}

function formatSize(bytes) {
  const units = ["B", "KB", "MB", "GB", "TB"];
  let value = bytes;
  let index = 0;
  while (value >= 1024 && index < units.length - 1) {
    value /= 1024;
    index += 1;
  }
  return `${value.toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

updateMode();

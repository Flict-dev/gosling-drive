import {
  api,
  type UploadInitiateResponse,
  type UploadPartUrlResponse,
} from "@/lib/api";

type UploadOptions = {
  folderId?: string | null;
  initiatePath?: string;
  omitFilename?: boolean;
  onProgress?: (percent: number) => void;
};

const PART_WORKER_CONCURRENCY = 4;

export async function uploadLargeFile(
  file: File,
  options: UploadOptions = {}
): Promise<void> {
  const initiateBody: Record<string, unknown> = {
    size_bytes: file.size,
    content_type: file.type || "application/octet-stream",
  };
  if (!options.omitFilename) {
    initiateBody.filename = file.name;
  }
  if (options.folderId) {
    initiateBody.folder_id = options.folderId;
  }

  const session = await api<UploadInitiateResponse>(
    options.initiatePath ?? "/uploads/initiate",
    {
      method: "POST",
      body: JSON.stringify(initiateBody),
    }
  );

  const completedParts: { part_number: number; etag: string }[] = [];
  let uploadedBytes = 0;
  let nextPart = 1;

  const workerCount = Math.min(PART_WORKER_CONCURRENCY, session.total_parts);
  const workers = Array.from({ length: workerCount }, async () => {
    while (nextPart <= session.total_parts) {
      const partNumber = nextPart;
      nextPart += 1;
      const start = (partNumber - 1) * session.part_size;
      const end = Math.min(start + session.part_size, file.size);
      const blob = file.slice(start, end);

      const urlPayload = await api<UploadPartUrlResponse>(
        `/uploads/${session.upload_session_id}/parts`,
        {
          method: "POST",
          body: JSON.stringify({ part_numbers: [partNumber] }),
        }
      );

      const response = await fetch(urlPayload.urls[0].url, {
        method: "PUT",
        body: blob,
      });
      if (!response.ok) {
        throw new Error(`Не удалось загрузить часть ${partNumber}`);
      }
      const etag = response.headers.get("ETag");
      if (!etag) {
        throw new Error(`MinIO не вернул ETag для части ${partNumber}`);
      }

      completedParts.push({ part_number: partNumber, etag });
      uploadedBytes += blob.size;
      options.onProgress?.(Math.round((uploadedBytes / file.size) * 100));
    }
  });

  await Promise.all(workers);

  await api(`/uploads/${session.upload_session_id}/complete`, {
    method: "POST",
    body: JSON.stringify({ parts: completedParts }),
  });
  options.onProgress?.(100);
}

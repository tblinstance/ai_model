export interface UploadedMediaAttachment {
  kind: "image" | "video";
  filename: string;
  mimeType: string;
  width: number;
  height: number;
  durationSeconds?: number;
  previewDataUrl: string;
  imageBase64?: string;
  framesBase64?: string[];
}

function readFileAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(new Error(`Failed to read ${file.name}`));
    reader.readAsDataURL(file);
  });
}

function loadImageElement(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error("Unsupported image format"));
    img.src = src;
  });
}

function drawResizedCanvas(
  source: CanvasImageSource,
  srcW: number,
  srcH: number,
  maxEdge: number
): { width: number; height: number; dataUrl: string } {
  const safeW = Math.max(1, srcW);
  const safeH = Math.max(1, srcH);
  const scale = Math.min(1, maxEdge / Math.max(safeW, safeH));
  const width = Math.max(16, Math.round(safeW * scale));
  const height = Math.max(16, Math.round(safeH * scale));
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    throw new Error("Canvas 2D context unavailable");
  }
  ctx.drawImage(source, 0, 0, width, height);
  return {
    width,
    height,
    dataUrl: canvas.toDataURL("image/png"),
  };
}

function seekVideoFrame(video: HTMLVideoElement, targetSec: number): Promise<void> {
  return new Promise((resolve) => {
    const onSeeked = () => {
      video.removeEventListener("seeked", onSeeked);
      resolve();
    };
    video.addEventListener("seeked", onSeeked, { once: true });
    video.currentTime = Math.max(0, targetSec);
  });
}

export async function prepareMediaAttachment(file: File): Promise<UploadedMediaAttachment> {
  if (file.type.startsWith("video/")) {
    const objectUrl = URL.createObjectURL(file);
    try {
      const video = document.createElement("video");
      video.muted = true;
      video.playsInline = true;
      video.preload = "auto";
      video.src = objectUrl;

      await new Promise<void>((resolve, reject) => {
        video.onloadedmetadata = () => resolve();
        video.onerror = () => reject(new Error("Could not decode uploaded video"));
      });

      const duration = Number.isFinite(video.duration) && video.duration > 0 ? video.duration : 1.0;
      const vidW = video.videoWidth || 320;
      const vidH = video.videoHeight || 240;
      const offsets = duration > 0.4 ? [0.15, 0.5, 0.85] : [0.0];
      const frames: string[] = [];
      let outW = vidW;
      let outH = vidH;

      for (const ratio of offsets) {
        await seekVideoFrame(video, duration * ratio);
        const snap = drawResizedCanvas(video, vidW, vidH, 320);
        outW = snap.width;
        outH = snap.height;
        frames.push(snap.dataUrl);
      }

      return {
        kind: "video",
        filename: file.name,
        mimeType: file.type || "video/mp4",
        width: outW,
        height: outH,
        durationSeconds: Number(duration.toFixed(1)),
        previewDataUrl: frames[0],
        framesBase64: frames,
      };
    } finally {
      URL.revokeObjectURL(objectUrl);
    }
  }

  if (file.type.startsWith("image/")) {
    const rawUrl = await readFileAsDataUrl(file);
    const img = await loadImageElement(rawUrl);
    const natW = img.naturalWidth || 256;
    const natH = img.naturalHeight || 256;
    // Preserve compact raw GIF bytes so animated GIF uploads keep multi-frame sequences
    if (file.type === "image/gif" && file.size <= 2 * 1024 * 1024) {
      return {
        kind: "image",
        filename: file.name,
        mimeType: "image/gif",
        width: natW,
        height: natH,
        previewDataUrl: rawUrl,
        imageBase64: rawUrl,
      };
    }
    const scaled = drawResizedCanvas(img, natW, natH, 512);
    return {
      kind: "image",
      filename: file.name,
      mimeType: "image/png",
      width: scaled.width,
      height: scaled.height,
      previewDataUrl: scaled.dataUrl,
      imageBase64: scaled.dataUrl,
    };
  }

  throw new Error("Please select an image (PNG, JPG, WebP, GIF) or video (MP4, WebM, MOV) file.");
}

export function attachmentToMetadata(attachment: UploadedMediaAttachment): Record<string, unknown> {
  return {
    media_kind: attachment.kind,
    media_filename: attachment.filename,
    reference_mime_type: attachment.mimeType,
    reference_width: attachment.width,
    reference_height: attachment.height,
    ...(attachment.durationSeconds !== undefined ? { duration_seconds: attachment.durationSeconds } : {}),
    ...(attachment.imageBase64 ? { reference_image_base64: attachment.imageBase64 } : {}),
    ...(attachment.framesBase64?.length ? { reference_frames_base64: attachment.framesBase64 } : {}),
  };
}


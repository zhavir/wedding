import { readFileSync } from 'node:fs';

// Test media stays local so uploads and previews do not depend on S3.
export const memoryImage = {
  name: 'memory.png',
  mimeType: 'image/png',
  buffer: readFileSync(new URL('./memory.png', import.meta.url))
};
export const previewImage = `data:image/png;base64,${memoryImage.buffer.toString('base64')}`;

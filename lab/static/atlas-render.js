/* SSI Atlas rendering
 *
 * Pure presentation of real SSI values. The backend attribution[grid][grid][C]
 * is never interpolated for numerical results; bicubic interpolation is used
 * ONLY to produce the displayed continuous overlay, as in the Visual Atlas.
 */
(function (root) {
  "use strict";

  function clamp(i, n) {
    return Math.max(0, Math.min(n - 1, i));
  }

  // Catmull-Rom cubic, only for rendering between cell-center samples.
  function cubic(a, b, c, d, t) {
    return b + 0.5 * t * (
      c - a + t * (2 * a - 5 * b + 4 * c - d
        + t * (3 * (b - c) + d - a))
    );
  }

  function sampleSmooth(grid, gx, gy) {
    const n = grid.length;
    const ix = Math.floor(gx);
    const iy = Math.floor(gy);
    const tx = gx - ix;
    const ty = gy - iy;
    const lines = [];
    for (let py = -1; py <= 2; py++) {
      const row = grid[clamp(iy + py, n)];
      lines.push(cubic(
        row[clamp(ix - 1, n)],
        row[clamp(ix, n)],
        row[clamp(ix + 1, n)],
        row[clamp(ix + 2, n)], tx,
      ));
    }
    return cubic(lines[0], lines[1], lines[2], lines[3], ty);
  }

  function signedLimit(matrix) {
    let max = 0;
    for (const row of matrix) for (const value of row) max = Math.max(max, Math.abs(value));
    return Math.max(max, 1e-12);
  }

  function overlayPixels(matrix, size, scale, opacity) {
    const n = matrix.length;
    const rgba = new Uint8ClampedArray(size * size * 4);
    const strength = Math.max(0, Math.min(1, opacity));
    for (let y = 0; y < size; y++) {
      const gy = (y + 0.5) * n / size - 0.5;
      for (let x = 0; x < size; x++) {
        const gx = (x + 0.5) * n / size - 0.5;
        const val = sampleSmooth(matrix, gx, gy);
        const t = Math.min(1, Math.abs(val) / Math.max(scale, 1e-12));
        const offset = (y * size + x) * 4;
        const positive = val >= 0;
        rgba[offset] = positive ? 189 : 39;
        rgba[offset + 1] = positive ? 61 : 110;
        rgba[offset + 2] = positive ? 70 : 159;
        // Transparent near zero; image details stay visible beneath the color.
        rgba[offset + 3] = Math.round(255 * 0.80 * strength *
          (t < 0.015 ? 0 : Math.pow(t, 0.82)));
      }
    }
    return rgba;
  }

  function contours(ctx, target) {
    if (!target || !target.data || !target.width || !target.height) return;
    const {data, width, height} = target;
    const sx = ctx.canvas.width / width;
    const sy = ctx.canvas.height / height;
    ctx.save();
    ctx.scale(sx, sy);
    ctx.beginPath();
    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        const at = y * width + x;
        if (!data[at]) continue;
        if (y === 0 || !data[at - width]) {ctx.moveTo(x, y); ctx.lineTo(x + 1, y);}
        if (x === width - 1 || !data[at + 1]) {ctx.moveTo(x + 1, y); ctx.lineTo(x + 1, y + 1);}
        if (y === height - 1 || !data[at + width]) {ctx.moveTo(x + 1, y + 1); ctx.lineTo(x, y + 1);}
        if (x === 0 || !data[at - 1]) {ctx.moveTo(x, y + 1); ctx.lineTo(x, y);}
      }
    }
    ctx.lineJoin = "round";
    ctx.lineCap = "round";
    ctx.lineWidth = 3.2 / Math.max(sx, sy);
    ctx.strokeStyle = "rgba(19, 29, 35, 0.90)";
    ctx.stroke();
    ctx.lineWidth = 1.75 / Math.max(sx, sy);
    ctx.strokeStyle = "rgba(246, 222, 139, 0.98)";
    ctx.stroke();
    ctx.restore();
  }

  function paint(canvas, input, matrix, scale, opacity, target, selection) {
    if (!canvas || !input || !input.complete || !input.naturalWidth) return false;
    const width = canvas.width;
    const height = canvas.height;
    const ctx = canvas.getContext("2d", {willReadFrequently: false});
    ctx.clearRect(0, 0, width, height);
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = "high";
    ctx.drawImage(input, 0, 0, width, height);

    if (matrix) {
      const size = Math.max(1, Math.min(width, height));
      const layer = document.createElement("canvas");
      layer.width = size;
      layer.height = size;
      const layerCtx = layer.getContext("2d");
      const rgba = overlayPixels(matrix, size, scale, opacity);
      layerCtx.putImageData(new ImageData(rgba, size, size), 0, 0);
      ctx.drawImage(layer, 0, 0, width, height);
    }
    // Atlas-style gold/ink boundary around the actual labeled target region.
    contours(ctx, target);

    if (selection) {
      const grid = matrix.length;
      const cellW = width / grid;
      const cellH = height / grid;
      ctx.save();
      ctx.lineWidth = 3;
      ctx.strokeStyle = "rgba(24,33,43,0.95)";
      ctx.strokeRect(selection.x * cellW + 2, selection.y * cellH + 2, cellW - 4, cellH - 4);
      ctx.lineWidth = 1.25;
      ctx.strokeStyle = "rgba(255,255,255,0.95)";
      ctx.strokeRect(selection.x * cellW + 5, selection.y * cellH + 5, cellW - 10, cellH - 10);
      ctx.restore();
    }
    return true;
  }

  function extractMask(img) {
    if (!img || !img.naturalWidth) return null;
    const width = img.naturalWidth, height = img.naturalHeight;
    const maskCanvas = document.createElement("canvas");
    maskCanvas.width = width; maskCanvas.height = height;
    const ctx = maskCanvas.getContext("2d", {willReadFrequently:true});
    ctx.drawImage(img, 0, 0);
    const pixels = ctx.getImageData(0, 0, width, height).data;
    const data = new Uint8Array(width * height);
    for (let i = 0; i < data.length; i++) data[i] = pixels[4 * i] >= 128 ? 1 : 0;
    return {width, height, data};
  }

  root.SSIAtlas = {paint, sampleSmooth, signedLimit, extractMask, overlayPixels};
})(window);

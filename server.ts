import express from 'express';
import { execFile } from 'child_process';
import fs from 'fs';
import os from 'os';
import path from 'path';
import { promisify } from 'util';
import { createServer as createViteServer } from 'vite';

const execFileAsync = promisify(execFile);

async function runPythonAction(action: string, payload: Record<string, unknown> = {}) {
  const serialized = JSON.stringify(payload);
  let tmpPayloadPath: string | null = null;
  const cliArgs = ['-m', 'wikiran_archive.main', '--api', action];
  if (serialized.length > 32768) {
    tmpPayloadPath = path.join(os.tmpdir(), `wikiran_payload_${Date.now()}_${Math.random().toString(36).slice(2)}.json`);
    fs.writeFileSync(tmpPayloadPath, serialized, 'utf-8');
    cliArgs.push('--payload-file', tmpPayloadPath);
  } else {
    cliArgs.push('--payload', serialized);
  }
  try {
    const { stdout } = await execFileAsync('python3', cliArgs, {
      cwd: process.cwd(),
      maxBuffer: 25 * 1024 * 1024,
    });
    return JSON.parse(stdout);
  } finally {
    if (tmpPayloadPath) {
      fs.unlink(tmpPayloadPath, () => {});
    }
  }
}

async function startServer() {
  const app = express();
  const PORT = 3000;

  app.use(express.json({ limit: '20mb' }));

  app.get('/api/overview', async (_req, res) => {
    try {
      const data = await runPythonAction('overview');
      res.json(data);
    } catch (err) {
      res.status(500).json({ ok: false, error: String(err) });
    }
  });

  app.post('/api/search', async (req, res) => {
    try {
      const data = await runPythonAction('search', req.body || {});
      res.json(data);
    } catch (err) {
      res.status(500).json({ ok: false, error: String(err) });
    }
  });

  app.post('/api/settings', async (req, res) => {
    try {
      const data = await runPythonAction('set_settings', { settings: req.body || {} });
      res.json(data);
    } catch (err) {
      res.status(500).json({ ok: false, error: String(err) });
    }
  });

  app.post('/api/schedule', async (req, res) => {
    try {
      const data = await runPythonAction('schedule_update', req.body || {});
      res.json(data);
    } catch (err) {
      res.status(500).json({ ok: false, error: String(err) });
    }
  });

  app.post('/api/schedule/run-now', async (_req, res) => {
    try {
      const data = await runPythonAction('schedule_run_now', {});
      res.json(data);
    } catch (err) {
      res.status(500).json({ ok: false, error: String(err) });
    }
  });

  app.post('/api/update-archive', async (req, res) => {
    try {
      const data = await runPythonAction('update_archive', req.body || {});
      res.json(data);
    } catch (err) {
      res.status(500).json({ ok: false, error: String(err) });
    }
  });

  app.get('/api/crawl-status', async (_req, res) => {
    try {
      const data = await runPythonAction('crawl_status', {});
      res.json(data);
    } catch (err) {
      res.status(500).json({ ok: false, error: String(err) });
    }
  });

  app.post('/api/stop-crawl', async (_req, res) => {
    try {
      const data = await runPythonAction('stop_crawl', {});
      res.json(data);
    } catch (err) {
      res.status(500).json({ ok: false, error: String(err) });
    }
  });

  app.get('/api/ofac/status', async (_req, res) => {
    try {
      const data = await runPythonAction('ofac_status', {});
      res.json(data);
    } catch (err) {
      res.status(500).json({ ok: false, error: String(err) });
    }
  });

  app.post('/api/ofac/sync', async (req, res) => {
    try {
      const data = await runPythonAction('ofac_sync', req.body || {});
      res.json(data);
    } catch (err) {
      res.status(500).json({ ok: false, error: String(err) });
    }
  });

  app.get('/api/opensanctions/status', async (_req, res) => {
    try {
      const data = await runPythonAction('opensanctions_status', {});
      res.json(data);
    } catch (err) {
      res.status(500).json({ ok: false, error: String(err) });
    }
  });

  app.post('/api/opensanctions/sync', async (req, res) => {
    try {
      const data = await runPythonAction('opensanctions_sync', req.body || {});
      res.json(data);
    } catch (err) {
      res.status(500).json({ ok: false, error: String(err) });
    }
  });

  app.post('/api/wikiran/sync-archives', async (req, res) => {
    try {
      const data = await runPythonAction('wikiran_sync_archives', req.body || {});
      res.json(data);
    } catch (err) {
      res.status(500).json({ ok: false, error: String(err) });
    }
  });

  app.post('/api/resume-job', async (req, res) => {
    try {
      const data = await runPythonAction('resume_job', req.body || {});
      res.json(data);
    } catch (err) {
      res.status(500).json({ ok: false, error: String(err) });
    }
  });

  app.post('/api/reconnaissance', async (_req, res) => {
    try {
      const data = await runPythonAction('reconnaissance');
      res.json(data);
    } catch (err) {
      res.status(500).json({ ok: false, error: String(err) });
    }
  });

  app.get('/api/export/:format', async (req, res) => {
    try {
      const fmt = (req.params.format || 'xlsx').toLowerCase();
      const rawEntities = typeof req.query.entities === 'string' ? req.query.entities : '';
      const entities = rawEntities
        ? rawEntities
            .split(',')
            .map((e) => e.trim().toLowerCase())
            .filter(Boolean)
        : undefined;
      const date_from =
        typeof req.query.date_from === 'string' && req.query.date_from.trim()
          ? req.query.date_from.trim()
          : undefined;
      const date_to =
        typeof req.query.date_to === 'string' && req.query.date_to.trim()
          ? req.query.date_to.trim()
          : undefined;
      const data = await runPythonAction('export', { format: fmt, entities, date_from, date_to });
      if (!data.ok || !data.path || !fs.existsSync(data.path)) {
        res.status(500).json({ ok: false, error: 'Export file could not be generated.' });
        return;
      }
      res.download(data.path, data.filename);
    } catch (err) {
      res.status(500).json({ ok: false, error: String(err) });
    }
  });

  app.post('/api/csv/import', async (req, res) => {
    try {
      const data = await runPythonAction('csv_import', req.body || {});
      res.json(data);
    } catch (err) {
      res.status(400).json({ ok: false, error: String(err) });
    }
  });

  app.post('/api/csv/view', async (req, res) => {
    try {
      const data = await runPythonAction('csv_view', req.body || {});
      res.json(data);
    } catch (err) {
      res.status(400).json({ ok: false, error: String(err) });
    }
  });

  app.get('/api/csv/download/:datasetId', async (req, res) => {
    try {
      const datasetId = Number(req.params.datasetId);
      const data = await runPythonAction('csv_view', { dataset_id: datasetId });
      const xlsxPath = data?.active_csv?.dataset?.xlsx_export_path;
      if (!xlsxPath || !fs.existsSync(xlsxPath)) {
        res.status(404).json({ ok: false, error: 'Converted Excel file not found.' });
        return;
      }
      res.download(xlsxPath, path.basename(xlsxPath));
    } catch (err) {
      res.status(500).json({ ok: false, error: String(err) });
    }
  });

  app.get('/api/watchlist/template/:format', async (req, res) => {
    try {
      const fmt = req.params.format === 'csv' ? 'csv' : 'xlsx';
      const data = await runPythonAction('watchlist_template', { format: fmt });
      if (!data.ok || !data.path || !fs.existsSync(data.path)) {
        res.status(500).json({ ok: false, error: 'Watchlist template could not be generated.' });
        return;
      }
      res.download(data.path, data.filename || `WikIran_Batch_Watchlist_Template.${fmt}`);
    } catch (err) {
      res.status(500).json({ ok: false, error: String(err) });
    }
  });

  app.post('/api/watchlist/screen', async (req, res) => {
    try {
      const data = await runPythonAction('watchlist_screen', req.body || {});
      res.json(data);
    } catch (err) {
      res.status(500).json({ ok: false, error: String(err) });
    }
  });

  app.get('/api/watchlist/report/download', (req, res) => {
    try {
      const reqPath = typeof req.query.path === 'string' ? req.query.path.trim() : '';
      const low = reqPath.toLowerCase();
      if (
        !reqPath ||
        (!low.endsWith('.xlsx') && !low.endsWith('.csv')) ||
        !path.basename(reqPath).startsWith('WikIran_Watchlist_Risk_Report_') ||
        !fs.existsSync(reqPath)
      ) {
        res.status(404).json({ ok: false, error: 'Watchlist risk report file not found.' });
        return;
      }
      res.download(reqPath, path.basename(reqPath));
    } catch (err) {
      res.status(500).json({ ok: false, error: String(err) });
    }
  });

  app.get('/api/leaks/catalog', async (req, res) => {
    try {
      const refresh = req.query.refresh === '1' || req.query.refresh === 'true';
      const data = await runPythonAction('leaks_catalog', { refresh });
      res.json(data);
    } catch (err) {
      res.status(500).json({ ok: false, error: String(err) });
    }
  });

  app.post('/api/leaks/download', async (req, res) => {
    try {
      const data = await runPythonAction('leaks_download', req.body || {});
      res.json(data);
    } catch (err) {
      res.status(500).json({ ok: false, error: String(err) });
    }
  });

  let cachedFullPortableZipPath = '';
  let cachedFullBackupZipPath = '';

  app.get('/api/download/windows-portable-lite-zip', async (_req, res) => {
    try {
      const data = await runPythonAction('windows_portable_lite_zip');
      if (!data.ok || !data.path || !fs.existsSync(data.path)) {
        res.status(500).json({ ok: false, error: 'Portable Windows Release ZIP could not be generated.' });
        return;
      }
      res.download(data.path, data.filename || 'WikIranArchive_Portable_Windows_Release.zip');
    } catch (err) {
      res.status(500).json({ ok: false, error: String(err) });
    }
  });

  app.post('/api/download/windows-portable-prepare', async (_req, res) => {
    try {
      const data = await runPythonAction('windows_portable_zip');
      if (!data.ok || !data.path || !fs.existsSync(data.path)) {
        res.status(500).json({ ok: false, error: 'Full Portable Windows ZIP could not be generated.' });
        return;
      }
      cachedFullPortableZipPath = data.path;
      const sizeBytes = fs.statSync(data.path).size;
      const chunkSize = 8 * 1024 * 1024; // 8 MB per chunk (well under Cloud Run's 32 MB limit)
      res.json({
        ok: true,
        filename: data.filename || 'WikIranArchive_Portable_Windows.zip',
        size_bytes: sizeBytes,
        chunk_size: chunkSize,
        total_chunks: Math.ceil(sizeBytes / chunkSize),
      });
    } catch (err) {
      res.status(500).json({ ok: false, error: String(err) });
    }
  });

  app.get('/api/download/windows-portable-chunk', (req, res) => {
    try {
      const zipPath = cachedFullPortableZipPath;
      if (!zipPath || !fs.existsSync(zipPath)) {
        res.status(404).json({ ok: false, error: 'Portable ZIP not prepared yet. Call prepare first.' });
        return;
      }
      const stat = fs.statSync(zipPath);
      const offset = Math.max(0, Number(req.query.offset || 0));
      const reqLen = Math.min(16 * 1024 * 1024, Math.max(1, Number(req.query.length || 8 * 1024 * 1024)));
      if (offset >= stat.size) {
        res.status(416).json({ ok: false, error: 'Offset out of range.' });
        return;
      }
      const end = Math.min(stat.size - 1, offset + reqLen - 1);
      const chunkLen = end - offset + 1;
      res.setHeader('Content-Type', 'application/octet-stream');
      res.setHeader('Content-Length', String(chunkLen));
      res.setHeader('Cache-Control', 'no-store');
      fs.createReadStream(zipPath, { start: offset, end }).pipe(res);
    } catch (err) {
      res.status(500).json({ ok: false, error: String(err) });
    }
  });

  app.post('/api/backup/full-prepare', async (req, res) => {
    try {
      const requestedPath = typeof req.body?.path === 'string' ? req.body.path.trim() : '';
      let zipPath = '';
      let filename = 'WikIran_Full_Portable_Backup.zip';
      if (requestedPath && fs.existsSync(requestedPath) && requestedPath.toLowerCase().endsWith('.zip')) {
        zipPath = requestedPath;
        filename = path.basename(requestedPath);
      } else {
        const data = await runPythonAction('backup_full_create');
        zipPath = data?.backup?.path || '';
        filename = data?.backup?.filename || filename;
      }
      if (!zipPath || !fs.existsSync(zipPath)) {
        res.status(500).json({ ok: false, error: 'Full backup ZIP could not be prepared.' });
        return;
      }
      cachedFullBackupZipPath = zipPath;
      const sizeBytes = fs.statSync(zipPath).size;
      const chunkSize = 8 * 1024 * 1024;
      res.json({
        ok: true,
        filename,
        size_bytes: sizeBytes,
        chunk_size: chunkSize,
        total_chunks: Math.ceil(sizeBytes / chunkSize),
      });
    } catch (err) {
      res.status(500).json({ ok: false, error: String(err) });
    }
  });

  app.get('/api/backup/full-chunk', (req, res) => {
    try {
      const zipPath = cachedFullBackupZipPath;
      if (!zipPath || !fs.existsSync(zipPath)) {
        res.status(404).json({ ok: false, error: 'Backup ZIP not prepared yet.' });
        return;
      }
      const stat = fs.statSync(zipPath);
      const offset = Math.max(0, Number(req.query.offset || 0));
      const reqLen = Math.min(16 * 1024 * 1024, Math.max(1, Number(req.query.length || 8 * 1024 * 1024)));
      if (offset >= stat.size) {
        res.status(416).json({ ok: false, error: 'Offset out of range.' });
        return;
      }
      const end = Math.min(stat.size - 1, offset + reqLen - 1);
      const chunkLen = end - offset + 1;
      res.setHeader('Content-Type', 'application/octet-stream');
      res.setHeader('Content-Length', String(chunkLen));
      res.setHeader('Cache-Control', 'no-store');
      fs.createReadStream(zipPath, { start: offset, end }).pipe(res);
    } catch (err) {
      res.status(500).json({ ok: false, error: String(err) });
    }
  });

  app.get('/api/download/windows-portable-zip', async (_req, res) => {
    try {
      const data = await runPythonAction('windows_portable_lite_zip');
      if (!data.ok || !data.path || !fs.existsSync(data.path)) {
        res.status(500).json({ ok: false, error: 'Portable Windows ZIP could not be generated.' });
        return;
      }
      res.download(data.path, data.filename || 'WikIranArchive_Portable_Windows_Release.zip');
    } catch (err) {
      res.status(500).json({ ok: false, error: String(err) });
    }
  });

  app.get('/api/download/windows-package', async (_req, res) => {
    try {
      const data = await runPythonAction('windows_package');
      if (!data.ok || !data.path || !fs.existsSync(data.path)) {
        res.status(500).json({ ok: false, error: 'Windows 11 package could not be generated.' });
        return;
      }
      res.download(data.path, data.filename || 'WikIran_Archive_Windows11_Clerk_Edition.zip');
    } catch (err) {
      res.status(500).json({ ok: false, error: String(err) });
    }
  });

  app.get('/api/download/windows-installer-exe', async (_req, res) => {
    try {
      const data = await runPythonAction('windows_installer_exe');
      if (!data.ok || !data.path || !fs.existsSync(data.path)) {
        res.status(500).json({
          ok: false,
          error: 'Windows installer .exe could not be generated.',
        });
        return;
      }
      res.download(data.path, data.filename || 'WikIranArchive_Setup.exe');
    } catch (err) {
      res.status(500).json({ ok: false, error: String(err) });
    }
  });

  app.get('/api/download/windows-shortcut', async (_req, res) => {
    try {
      const data = await runPythonAction('windows_installer_exe');
      if (!data.ok || !data.path || !fs.existsSync(data.path)) {
        res.status(500).json({
          ok: false,
          error: 'Windows installer .exe could not be generated.',
        });
        return;
      }
      res.download(data.path, data.filename || 'WikIranArchive_Setup.exe');
    } catch (err) {
      res.status(500).json({ ok: false, error: String(err) });
    }
  });

  app.get('/api/download/windows-app-html', async (_req, res) => {
    try {
      const data = await runPythonAction('windows_app_html');
      if (!data.ok || !data.path || !fs.existsSync(data.path)) {
        res.status(500).json({
          ok: false,
          error: 'Windows 11 ready app could not be generated.',
        });
        return;
      }
      res.download(
        data.path,
        data.filename || 'WikIran_Archive_Windows11_Ready_App.html'
      );
    } catch (err) {
      res.status(500).json({ ok: false, error: String(err) });
    }
  });

  app.post('/api/backup/create', async (_req, res) => {
    try {
      const data = await runPythonAction('backup_create');
      res.json(data);
    } catch (err) {
      res.status(500).json({ ok: false, error: String(err) });
    }
  });

  app.post('/api/backup/full-create', async (_req, res) => {
    try {
      const data = await runPythonAction('backup_full_create');
      res.json(data);
    } catch (err) {
      res.status(500).json({ ok: false, error: String(err) });
    }
  });

  app.get('/api/backup/full-download', async (req, res) => {
    try {
      const requestedPath =
        typeof req.query.path === 'string' && req.query.path.trim()
          ? req.query.path.trim()
          : '';
      if (requestedPath && fs.existsSync(requestedPath) && requestedPath.endsWith('.zip')) {
        res.download(requestedPath, path.basename(requestedPath));
        return;
      }
      const data = await runPythonAction('backup_full_create');
      const zipPath = data?.backup?.path;
      if (!data?.ok || !zipPath || !fs.existsSync(zipPath)) {
        res.status(500).json({ ok: false, error: 'Full portable backup package could not be generated.' });
        return;
      }
      res.download(zipPath, data.backup.filename || 'WikIran_Full_Portable_Backup.zip');
    } catch (err) {
      res.status(500).json({ ok: false, error: String(err) });
    }
  });

  app.post('/api/backup/full-restore-upload', async (req, res) => {
    const rawName = String(req.headers['x-backup-filename'] || 'uploaded_backup.zip');
    const ext = rawName.toLowerCase().endsWith('.db') ? '.db' : '.zip';
    const tmpFile = path.join(os.tmpdir(), `wikiran_restore_${Date.now()}${ext}`);
    try {
      await new Promise<void>((resolve, reject) => {
        const ws = fs.createWriteStream(tmpFile);
        req.pipe(ws);
        ws.on('finish', () => resolve());
        ws.on('error', reject);
        req.on('error', reject);
      });
      const data = await runPythonAction('backup_full_restore', {
        path: tmpFile,
        confirmed: true,
      });
      res.json(data);
    } catch (err) {
      res.status(400).json({ ok: false, error: String(err) });
    } finally {
      fs.unlink(tmpFile, () => {});
    }
  });

  app.post('/api/backup/restore', async (req, res) => {
    try {
      const data = await runPythonAction('backup_restore', req.body || {});
      res.json(data);
    } catch (err) {
      res.status(400).json({ ok: false, error: String(err) });
    }
  });

  app.post('/api/integrity-check', async (_req, res) => {
    try {
      const data = await runPythonAction('integrity_check');
      res.json(data);
    } catch (err) {
      res.status(500).json({ ok: false, error: String(err) });
    }
  });

  app.get('/api/tests', async (_req, res) => {
    try {
      const { stdout, stderr } = await execFileAsync(
        'python3',
        ['-m', 'unittest', 'discover', '-s', 'tests', '-v'],
        { cwd: process.cwd() }
      );
      res.json({ ok: true, output: `${stdout}\n${stderr}`.trim() });
    } catch (err: unknown) {
      const e = err as { stdout?: string; stderr?: string; message?: string };
      res.json({
        ok: false,
        output: `${e.stdout || ''}\n${e.stderr || e.message || ''}`.trim(),
      });
    }
  });

  const DOC_FILES: Record<string, string> = {
    reconnaissance: 'RECONNAISSANCE_REPORT.md',
    architecture: 'ARCHITECTURE.md',
    schema: 'DATABASE_SCHEMA.md',
    manual_fa: 'OPERATOR_MANUAL_FA.md',
    manual_en: 'OPERATOR_MANUAL_EN.md',
    status: 'PROJECT_STATUS.md',
    pyside_ui: 'wikiran_archive/ui/main_window.py',
    migrations_py: 'wikiran_archive/database/migrations.py',
    recon_py: 'wikiran_archive/collector/reconnaissance.py',
  };

  app.get('/api/docs/:key', (req, res) => {
    const relPath = DOC_FILES[req.params.key];
    if (!relPath) {
      res.status(404).json({ ok: false, error: 'Document not found' });
      return;
    }
    const fullPath = path.resolve(process.cwd(), relPath);
    if (!fs.existsSync(fullPath)) {
      res.status(404).json({ ok: false, error: 'File missing on disk' });
      return;
    }
    res.json({
      ok: true,
      filename: relPath,
      content: fs.readFileSync(fullPath, 'utf-8'),
    });
  });

  if (process.env.NODE_ENV !== 'production') {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), 'dist');
    app.use(express.static(distPath));
    app.get('*', (_req, res) => {
      res.sendFile(path.join(distPath, 'index.html'));
    });
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`WikIran Archive Desktop Bridge running on http://localhost:${PORT}`);
  });
}

startServer();

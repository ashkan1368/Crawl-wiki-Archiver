import React, { useEffect, useState, useCallback } from 'react';
import {
  Search,
  BookOpen,
  FolderKanban,
  Building2,
  Tags,
  FileSpreadsheet,
  History,
  Settings,
  HelpCircle,
  LayoutDashboard,
  RefreshCw,
  HardDriveDownload,
  ShieldCheck,
  ExternalLink,
  CheckCircle2,
  AlertTriangle,
  Play,
  FileCode2,
  Globe,
  Clock,
  Table,
  Upload,
  Menu,
  X,
  Eye,
  Unlock,
  Lock,
  Layers,
  Wifi,
  WifiOff,
  Square,
  Download,
  Calendar,
  Activity,
  HardDrive,
  ChevronDown,
  ChevronRight,
  ClipboardList,
} from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import { Language, NavSection, UI_LABELS } from './i18n';
import { BatchWatchlistPanel } from './components/BatchWatchlistPanel';
import { TargetedLeakDownloaderPanel } from './components/TargetedLeakDownloaderPanel';

interface Article {
  id: number;
  original_pub_id: string;
  title: string;
  subtitle: string;
  author: string;
  publication_date: string;
  summary: string;
  editorial_content: string;
  categories_en: string;
  categories_fa: string;
  organizations_list: string;
  tags_list: string;
  source_url: string;
  retrieved_at: string;
  last_verified_at: string;
  extraction_status: string;
  content_hash: string;
  record_version: number;
}

interface Publication {
  id: number;
  original_pub_id: string;
  title: string;
  native_title: string;
  publication_date: string;
  description: string;
  categories_en: string;
  categories_fa: string;
  source_url: string;
  retrieved_at: string;
  last_verified_at: string;
  extraction_status: string;
  content_hash: string;
  record_version: number;
  inventory: Array<{
    data_type: string;
    reported_count_label: string;
    safety_policy_applied: string;
  }>;
}

interface Organization {
  id: number;
  name: string;
  native_name: string;
  acronym: string;
  org_type: string;
  description: string;
  linked_articles_count: number;
  linked_entities_count: number;
  source_url: string;
  retrieved_at: string;
}

interface Category {
  id: number;
  slug: string;
  name_en: string;
  name_fa: string;
  description: string;
  article_count: number;
  publication_count: number;
}

interface CollectionJob {
  id: number;
  job_uuid: string;
  job_type: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  total_discovered: number;
  processed_count: number;
  new_records_count: number;
  updated_records_count: number;
  skipped_unchanged_count: number;
  blocked_sensitive_count: number;
  failed_count: number;
  checkpoint_data: string;
  error_summary: string | null;
}

interface CollectionHistoryItem {
  id: number;
  job_id: number;
  target_url: string;
  record_type: string;
  http_status: number | null;
  action_taken: string;
  timestamp: string;
  message: string;
}

interface BackupItem {
  filename: string;
  path: string;
  size_bytes: number;
  created_at: string;
  integrity_verified: boolean;
}

interface TrendPoint {
  period: string;
  articles_collected: number;
  catalogues_collected: number;
  records_added: number;
  total_database_growth: number;
}

interface ScheduleState {
  enabled: boolean;
  frequency: string;
  time_utc: string;
  day_of_week: string;
  max_items_per_run: number;
  last_run_at: string;
  next_run_at: string;
  runner_status: string;
}

interface CsvDatasetMeta {
  id: number;
  dataset_name: string;
  original_filename: string;
  headers: string[];
  row_count: number;
  xlsx_export_path?: string;
  retrieved_at?: string;
}

interface CsvRowRecord {
  id: number;
  row_number: number;
  cells: Record<string, string>;
  searchable_text: string;
}

interface ActiveCsvPayload {
  dataset: CsvDatasetMeta | null;
  rows: CsvRowRecord[];
  total_matching_count?: number;
  displayed_count?: number;
  is_subset?: boolean;
  preview_all?: boolean;
  cross_dataset_audit?: boolean;
}

interface OverviewPayload {
  ok: boolean;
  stats: {
    articles_count: number;
    publications_count: number;
    organizations_count: number;
    entities_count: number;
    categories_count: number;
    sources_count: number;
    file_inventory_count: number;
    jobs_count: number;
    changes_count: number;
    last_job: CollectionJob | null;
  };
  trends: TrendPoint[];
  schedule: ScheduleState;
  csv_datasets: CsvDatasetMeta[];
  active_csv: ActiveCsvPayload;
  settings: Record<string, string>;
  articles: Article[];
  publications: Publication[];
  organizations: Organization[];
  categories: Category[];
  tags?: Array<{
    id: number;
    slug: string;
    name: string;
    linked_articles_count: number;
    linked_articles_titles?: string;
  }>;
  sources: Array<Record<string, unknown>>;
  jobs: CollectionJob[];
  history: CollectionHistoryItem[];
  changes: Array<Record<string, unknown>>;
  backups: BackupItem[];
  integrity: { verified: boolean; message: string };
  logs: string[];
  paths: {
    base_dir: string;
    db_path: string;
    backups_dir: string;
    exports_dir: string;
    logs_dir: string;
  };
  storage_volume?: {
    db_bytes: number;
    backups_bytes: number;
    exports_bytes: number;
    logs_bytes: number;
    text_bytes: number;
    total_bytes: number;
    db_size_label: string;
    total_size_label: string;
    text_size_label: string;
    total_records: number;
    articles_count: number;
    publications_count: number;
    csv_rows_count: number;
    ofac_entities_count?: number;
    opensanctions_count?: number;
    wikiran_docs_count?: number;
    fts_indexed_count: number;
  };
  ofac_summary?: {
    total_entities: number;
    sdn_count: number;
    consolidated_count: number;
    iran_related_count: number;
    individuals_count: number;
    organizations_count: number;
    vessels_count: number;
    aircraft_count: number;
    last_publication_id: string;
    last_date_published: string;
    last_synced_at: string;
    sanctions_lists: string[];
    sanctions_programs_count: number;
    top_programs: Array<{ program: string; count: number }>;
    sample_iran_entities: Array<Record<string, unknown>>;
  };
  opensanctions_summary?: {
    total_entities: number;
    iran_related_count: number;
    dataset_name: string;
    last_change: string;
    last_sync_at: string;
    last_check_at: string;
    catalog_datasets_count: number;
    source_datasets_count: number;
    schema_counts: Array<{ schema: string; count: number }>;
    top_source_lists: Array<{ list: string; count: number }>;
    sample_iran_entities: Array<Record<string, unknown>>;
  };
  wikiran_docs_summary?: {
    total: number;
    front_companies: number;
    vessels: number;
    leaked_emails: number;
    leaked_files: number;
    other_docs: number;
    last_sync_at: string;
  };
  frontier_stats?: {
    pending: number;
    crawled: number;
    failed: number;
    blocked: number;
    total: number;
  };
}

export default function App() {
  const [data, setData] = useState<OverviewPayload | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [activeNav, setActiveNav] = useState<NavSection>('dashboard');
  const [lang, setLang] = useState<Language>('en');
  const [bannerMessage, setBannerMessage] = useState<{ text: string; type: 'info' | 'error' } | null>(null);
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [storagePathInput, setStoragePathInput] = useState<string>('C:\\WikIranArchive');

  // Responsive sidebar drawer state for smaller window sizes
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(false);

  // Application Workflow Modal state (triggers on first launch + accessible via "How to work?" button)
  const [showWorkflowModal, setShowWorkflowModal] = useState<boolean>(() => {
    try {
      return localStorage.getItem('wikiran_workflow_modal_seen_v2') !== 'true';
    } catch {
      return true;
    }
  });

  // Network connectivity state (auto-detects browser online/offline + allows manual offline test toggle)
  const [isOffline, setIsOffline] = useState<boolean>(() =>
    typeof navigator !== 'undefined' ? !navigator.onLine : false
  );

  // Step-by-step live pipeline walkthrough state on Dashboard
  const [activePipelineStep, setActivePipelineStep] = useState<number>(0);
  const [pipelineLog, setPipelineLog] = useState<string | null>(null);

  // Search filters state
  const [searchQuery, setSearchQuery] = useState('');
  const [filterCategory, setFilterCategory] = useState('ALL');
  const [filterOrg, setFilterOrg] = useState('ALL');
  const [filterType, setFilterType] = useState('ALL');
  const [filterDateFrom, setFilterDateFrom] = useState('');
  const [filterDateTo, setFilterDateTo] = useState('');
  const [searchResults, setSearchResults] = useState<Array<Record<string, unknown>> | null>(null);

  // Selected article reader
  const [selectedArticle, setSelectedArticle] = useState<Article | null>(null);

  // Confirm restore state
  const [confirmRestorePath, setConfirmRestorePath] = useState<string | null>(null);

  // Scheduled Collection form state
  const [schedEnabled, setSchedEnabled] = useState<boolean>(true);
  const [schedFreq, setSchedFreq] = useState<string>('daily');
  const [schedTime, setSchedTime] = useState<string>('02:00');
  const [schedDay, setSchedDay] = useState<string>('sunday');
  const [schedMaxItems, setSchedMaxItems] = useState<number>(6);

  // CSV-to-Excel Workbench state (including Preview All Matching Records & Cross-Dataset Audit)
  const [selectedCsvId, setSelectedCsvId] = useState<number | null>(null);
  const [csvFilterQuery, setCsvFilterQuery] = useState<string>('');
  const [csvPreviewAll, setCsvPreviewAll] = useState<boolean>(false);
  const [csvCrossDatasetAudit, setCsvCrossDatasetAudit] = useState<boolean>(false);
  const [activeCsvView, setActiveCsvView] = useState<ActiveCsvPayload | null>(null);

  // Export Report Wizard state: allows user to choose specific data entities (OFAC + OpenSanctions + WikIran) & optional date range
  const [wizardEntities, setWizardEntities] = useState<
    Array<
      | 'ofac_iran'
      | 'ofac_all'
      | 'opensanctions_iran'
      | 'opensanctions_all'
      | 'articles'
      | 'publications'
      | 'organizations'
      | 'tags'
    >
  >(['ofac_iran', 'opensanctions_iran', 'articles', 'publications']);
  const [wizardDateFrom, setWizardDateFrom] = useState<string>('');
  const [wizardDateTo, setWizardDateTo] = useState<string>('');

  // Collapsible optional archive reference tables drawer in sidebar (separated from core daily tools)
  const [showArchiveTablesNav, setShowArchiveTablesNav] = useState<boolean>(false);

  // Stylish Human-Readable Converter viewer tab ('ofac_iran' live preview vs uploaded 'csv' tables)
  const [converterTab, setConverterTab] = useState<'ofac_iran' | 'csv'>('ofac_iran');
  const [ofacViewerQuery, setOfacViewerQuery] = useState<string>('');

  // Live Crawl / Spider Activity Monitor state
  const [crawlElapsedSec, setCrawlElapsedSec] = useState<number>(0);
  const [crawlModeLabel, setCrawlModeLabel] = useState<string>('');
  const [liveCrawlStatus, setLiveCrawlStatus] = useState<{
    active_job: CollectionJob | null;
    recent_history: CollectionHistoryItem[];
    articles_count: number;
    publications_count: number;
    stop_requested: boolean;
    frontier_stats?: OverviewPayload['frontier_stats'];
    storage_volume?: OverviewPayload['storage_volume'];
  } | null>(null);

  // Quick source-scope tab inside Universal Search results (All vs OFAC vs OpenSanctions vs WikIran)
  const [searchScopeTab, setSearchScopeTab] = useState<'ALL' | 'OFAC' | 'OPENSANCTIONS' | 'WIKIRAN'>('ALL');
  const [includeLiveWikIran, setIncludeLiveWikIran] = useState<boolean>(true);
  const [activeLeakSourceFilter, setActiveLeakSourceFilter] = useState<string>('');
  const [wikiranLiveMeta, setWikiranLiveMeta] = useState<{
    online: boolean;
    total_label: string;
    total_int: number;
    facets: Array<{ source: string; label: string; amount: number }>;
    fetched_count: number;
    cached_new_count: number;
    search_url: string;
    error?: string;
  } | null>(null);
  const [wikiranSyncNote, setWikiranSyncNote] = useState<string | null>(null);
  const [ofacStatusNote, setOfacStatusNote] = useState<string | null>(null);
  const [osStatusNote, setOsStatusNote] = useState<string | null>(null);
  const [fullBackupMsg, setFullBackupMsg] = useState<string | null>(null);

  const toggleWizardEntity = (
    entity:
      | 'ofac_iran'
      | 'ofac_all'
      | 'opensanctions_iran'
      | 'opensanctions_all'
      | 'articles'
      | 'publications'
      | 'organizations'
      | 'tags'
  ) => {
    setWizardEntities((prev) =>
      prev.includes(entity) ? prev.filter((item) => item !== entity) : [...prev, entity]
    );
  };

  const [chunkDownloadProgress, setChunkDownloadProgress] = useState<{
    label: string;
    percent: number;
    loadedMb: string;
    totalMb: string;
  } | null>(null);

  const downloadChunkedZip = async (
    prepareUrl: string,
    chunkUrl: string,
    prepareBody: Record<string, unknown>,
    displayLabel: string
  ) => {
    setChunkDownloadProgress({
      label: displayLabel,
      percent: 2,
      loadedMb: '0.0',
      totalMb: '...',
    });
    setFullBackupMsg(null);
    try {
      const prepRes = await fetch(prepareUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(prepareBody),
      });
      const prep = await prepRes.json();
      if (!prep.ok || !prep.size_bytes) {
        throw new Error(prep.error || 'Could not prepare ZIP package on server.');
      }

      const totalBytes = Number(prep.size_bytes);
      const chunkSize = Number(prep.chunk_size || 8 * 1024 * 1024);
      const filename = String(prep.filename || 'WikIranArchive_Portable_Windows.zip');
      const totalMb = (totalBytes / (1024 * 1024)).toFixed(1);
      const chunks: BlobPart[] = [];
      let loaded = 0;

      while (loaded < totalBytes) {
        const len = Math.min(chunkSize, totalBytes - loaded);
        const cRes = await fetch(`${chunkUrl}?offset=${loaded}&length=${len}`);
        if (!cRes.ok) {
          throw new Error(`Chunk download failed at byte ${loaded} (HTTP ${cRes.status})`);
        }
        const buf = await cRes.arrayBuffer();
        chunks.push(buf);
        loaded += buf.byteLength;
        const pct = Math.min(99, Math.round((loaded / totalBytes) * 100));
        setChunkDownloadProgress({
          label: `${displayLabel} — ${filename}`,
          percent: pct,
          loadedMb: (loaded / (1024 * 1024)).toFixed(1),
          totalMb,
        });
      }

      const blob = new Blob(chunks, { type: 'application/zip' });
      const blobUrl = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = blobUrl;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.setTimeout(() => URL.revokeObjectURL(blobUrl), 15000);
      setFullBackupMsg(
        lang === 'fa'
          ? `فایل ${filename} (${totalMb} MB) با موفقیت آماده و دانلود شد.`
          : `Downloaded ${filename} (${totalMb} MB) successfully.`
      );
    } catch (err) {
      setFullBackupMsg(
        lang === 'fa'
          ? `خطا در دانلود بسته: ${String(err)}`
          : `Download error: ${String(err)}`
      );
    } finally {
      setChunkDownloadProgress(null);
    }
  };

  // Helper to highlight search query terms with a bold yellow background inside summaries and excerpts
  const highlightSearchTerms = (text: string, rawQuery: string): React.ReactNode => {
    if (!text) return '';
    const cleaned = (rawQuery || '')
      .replace(/["*]/g, ' ')
      .split(/\s+/)
      .map((term) => term.trim())
      .filter(
        (term) =>
          term.length > 0 && !['AND', 'OR', 'NOT'].includes(term.toUpperCase())
      );
    if (cleaned.length === 0) return text;

    // Sort longer terms first and escape regex special characters
    const uniqueTerms = Array.from(new Set(cleaned)).sort((a, b) => b.length - a.length);
    const escaped = uniqueTerms.map((term) => term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
    const pattern = new RegExp(`(${escaped.join('|')})`, 'gi');
    const parts = text.split(pattern);

    return parts.map((part, idx) => {
      const isMatch = uniqueTerms.some((term) => part.toLowerCase() === term.toLowerCase());
      if (isMatch) {
        return (
          <mark
            key={idx}
            className="bg-yellow-300 text-slate-950 font-bold px-1 rounded-xs"
          >
            {part}
          </mark>
        );
      }
      return <React.Fragment key={idx}>{part}</React.Fragment>;
    });
  };

  // Engineering / Doc viewer
  const [docKey, setDocKey] = useState<string>('reconnaissance');
  const [docContent, setDocContent] = useState<{ filename: string; content: string } | null>(null);
  const [testOutput, setTestOutput] = useState<string | null>(null);

  const t = UI_LABELS[lang];
  const isRtl = lang === 'fa';

  const closeWorkflowModal = () => {
    setShowWorkflowModal(false);
    try {
      localStorage.setItem('wikiran_workflow_modal_seen_v2', 'true');
    } catch {
      // ignore storage errors
    }
  };

  const fetchOverview = useCallback(async () => {
    try {
      const res = await fetch('/api/overview');
      const json: OverviewPayload = await res.json();
      if (json.ok) {
        setData(json);
        const savedLang = json.settings?.ui_language === 'fa' ? 'fa' : 'en';
        setLang(savedLang);
        if (json.settings?.custom_storage_path) {
          setStoragePathInput(json.settings.custom_storage_path);
        } else if (json.paths?.base_dir) {
          setStoragePathInput(json.paths.base_dir);
        }
        if (json.schedule) {
          setSchedEnabled(json.schedule.enabled);
          setSchedFreq(json.schedule.frequency);
          setSchedTime(json.schedule.time_utc);
          setSchedDay(json.schedule.day_of_week);
          setSchedMaxItems(json.schedule.max_items_per_run);
        }
        if (json.active_csv) {
          setActiveCsvView(json.active_csv);
          setSelectedCsvId(json.active_csv.dataset?.id ?? null);
        }
      }
    } catch {
      setBannerMessage({
        text:
          lang === 'fa'
            ? 'خطا در ارتباط با موتور محلی پایتون.'
            : 'Could not connect to local Python archive engine.',
        type: 'error',
      });
    } finally {
      setLoading(false);
    }
  }, [lang]);

  useEffect(() => {
    fetchOverview();
  }, [fetchOverview]);

  useEffect(() => {
    document.documentElement.dir = isRtl ? 'rtl' : 'ltr';
    document.documentElement.lang = lang;
  }, [isRtl, lang]);

  useEffect(() => {
    const handleOnline = () => setIsOffline(false);
    const handleOffline = () => setIsOffline(true);
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // Real-time live polling & elapsed timer while Lookup Server / Deep Spider crawling is active
  const isCrawlingNow = busyAction === 'update' || busyAction === 'pipeline';

  useEffect(() => {
    if (!isCrawlingNow) return;
    setCrawlElapsedSec(0);
    let cancelled = false;

    const tickTimer = window.setInterval(() => {
      setCrawlElapsedSec((s) => s + 1);
    }, 1000);

    const pollStatus = async () => {
      try {
        const res = await fetch('/api/crawl-status');
        const json = await res.json();
        if (!cancelled && json.ok) {
          setLiveCrawlStatus({
            active_job: json.active_job || null,
            recent_history: json.recent_history || [],
            articles_count: json.articles_count ?? 0,
            publications_count: json.publications_count ?? 0,
            stop_requested: Boolean(json.stop_requested),
          });
        }
      } catch {
        // ignore transient poll errors while SQLite writes
      }
    };

    pollStatus();
    const pollTimer = window.setInterval(pollStatus, 1300);

    return () => {
      cancelled = true;
      window.clearInterval(tickTimer);
      window.clearInterval(pollTimer);
    };
  }, [isCrawlingNow]);

  const loadDoc = useCallback(async (key: string) => {
    setDocKey(key);
    try {
      const res = await fetch(`/api/docs/${key}`);
      const json = await res.json();
      if (json.ok) {
        setDocContent({ filename: json.filename, content: json.content });
      }
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    if (activeNav === 'help' || activeNav === 'settings') {
      loadDoc(activeNav === 'help' ? (lang === 'fa' ? 'manual_fa' : 'manual_en') : docKey);
    }
  }, [activeNav, lang, docKey, loadDoc]);

  const handleLanguageSwitch = async (nextLang: Language) => {
    setLang(nextLang);
    await fetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ui_language: nextLang }),
    });
  };

  const handleSaveStoragePath = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const cleanedPath = storagePathInput.trim() || 'C:\\WikIranArchive';
    setBusyAction('save-storage-path');
    try {
      const res = await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ custom_storage_path: cleanedPath }),
      });
      const json = await res.json();
      await fetchOverview();
      if (json.ok) {
        setBannerMessage({
          text:
            lang === 'fa'
              ? `مسیر ذخیره‌سازی اطلاعات با موفقیت روی «${cleanedPath}» تنظیم شد.`
              : `Storage Path updated to "${cleanedPath}". Database, Excel exports, and backups will use this directory.`,
          type: 'info',
        });
      }
    } finally {
      setBusyAction(null);
    }
  };

  // Toggle between Full Unredacted Archive Mode (strict_sensitive_exclusion = 'false') and Filtered Mode
  const handleToggleArchiveScope = async (enableFullUnredacted: boolean) => {
    setBusyAction('toggle-scope');
    try {
      const res = await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          strict_sensitive_exclusion: enableFullUnredacted ? 'false' : 'true',
        }),
      });
      const json = await res.json();
      await fetchOverview();
      if (json.ok) {
        if (json.active_csv) {
          setActiveCsvView(json.active_csv);
          setSelectedCsvId(json.active_csv.dataset?.id ?? null);
          setCsvPreviewAll(true);
        }
        setBannerMessage({
          text: enableFullUnredacted
            ? lang === 'fa'
              ? 'حالت آرشیو کامل بدون حذفیات فعال شد: مکاتبات (/document/emails/*)، فایل‌ها (/document/files/*) و اسناد بانکی اکنون در جستجو و جدول اکسل در دسترس هستند.'
              : 'Full Unredacted Archive Mode activated: All correspondence (/document/emails/*), raw files (/document/files/*), and banking records are now unlocked and searchable.'
            : lang === 'fa'
            ? 'حالت فیلتر عمومی فعال شد.'
            : 'Switched to Filtered Public Scope mode.',
          type: 'info',
        });
      }
    } finally {
      setBusyAction(null);
    }
  };

  // Stop active deep spider crawl safely at the current page checkpoint
  const handleStopCrawl = async () => {
    try {
      setPipelineLog(
        lang === 'fa'
          ? 'درخواست توقف ثبت شد: خزنده در حال ذخیره نقطه بازیابی (Checkpoint) در دیتابیس SQLite و توقف ایمن است...'
          : 'Stop requested: Spider is saving a verified checkpoint in SQLite and halting cleanly...'
      );
      await fetch('/api/stop-crawl', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      await fetchOverview();
      setBannerMessage({
        text:
          lang === 'fa'
            ? 'عملیات خزش و دریافت داده با موفقیت متوقف شد. تمام رکوردهای دریافت‌شده تا این لحظه در SQLite ذخیره شدند و نقطه بازیابی (Checkpoint) برای ادامه در آینده ثبت گردید.'
            : 'Crawling stopped safely by user. All records downloaded so far are saved in SQLite with a verified checkpoint (Resume anytime in Collection History).',
        type: 'info',
      });
    } finally {
      setBusyAction(null);
    }
  };

  // Interactive Step-by-Step Pipeline Runner on the Dashboard
  const handleRunVisualPipeline = async () => {
    setCrawlModeLabel(
      lang === 'fa' ? 'اجرای ۴ مرحله‌ای زنده (Live Pipeline)' : '4-Step Live Pipeline'
    );
    setBusyAction('pipeline');
    try {
      setActivePipelineStep(1);
      setPipelineLog(
        lang === 'fa'
          ? 'مرحله ۱ از ۴: خزش عمیق (Deep Spider) در robots.txt، نقشه سایت، تمام صفحات مقالات (/search?tabType=articles&page=1..N) و فهرست اسناد (/leaks و /archives)...'
          : 'Step 1 of 4: Deep Spider inspecting robots.txt, sitemap.xml, paginated article feeds (/search?tabType=articles&page=1..N), /leaks & /archives...'
      );
      await new Promise((r) => setTimeout(r, 500));

      setActivePipelineStep(2);
      setPipelineLog(
        lang === 'fa'
          ? 'مرحله ۲ از ۴: دنبال کردن تمام لینک‌های داخلی مانند عنکبوت (Spider) و استخراج مقالات، انتشارات، ایمیل‌ها و فایل‌ها...'
          : 'Step 2 of 4: Spidering internal links across pages and extracting articles, publications, correspondence & files...'
      );
      const res = await fetch('/api/update-archive', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ max_items: 12, deep_spider: true }),
      });
      const json = await res.json();

      setActivePipelineStep(3);
      setPipelineLog(
        lang === 'fa'
          ? 'مرحله ۳ از ۴: نرمال‌سازی تاریخ‌ها، محاسبه هش SHA-256 و نمایه‌سازی تمام داده‌ها در موتور جستجوی SQLite FTS5...'
          : 'Step 3 of 4: Normalizing dates, verifying SHA-256 hashes, and indexing all tables & CSV rows in SQLite FTS5...'
      );
      await new Promise((r) => setTimeout(r, 350));

      setActivePipelineStep(4);
      await fetchOverview();
      const status = json?.job?.status;
      const processed = json?.job?.processed_count ?? 0;
      const discovered = json?.job?.total_discovered ?? processed;
      const newAdded = json?.job?.new_records_count ?? 0;
      if (status === 'INTERRUPTED') {
        setPipelineLog(
          lang === 'fa'
            ? `خزش توسط کاربر متوقف شد: ${newAdded} رکورد جدید ذخیره شد (${processed} از ${discovered} لینک بررسی شد).`
            : `Spider crawl stopped at checkpoint: ${newAdded} NEW records saved (${processed} of ${discovered} discovered links processed).`
        );
      } else {
        setPipelineLog(
          lang === 'fa'
            ? `عملیات ۴ مرحله‌ای خزش عمیق کامل شد: ${newAdded} رکورد جدید دانلود شد (${processed} صفحه از ${discovered} لینک کشف‌شده بررسی شد).`
            : `All 4 Pipeline Steps Verified: ${newAdded} NEW records downloaded (${processed} pages processed across ${discovered} spider-discovered links).`
        );
      }
    } finally {
      setBusyAction(null);
    }
  };

  const handleSyncWikIranArchives = async (target: 'both' | 'front-companies' | 'vessels' = 'both') => {
    if (isOffline) {
      setBannerMessage({
        text:
          lang === 'fa'
            ? 'آفلاین: برای همگام‌سازی آرشیو شرکت‌های پوششی و کشتی‌های ویکی‌ایران نیاز به اینترنت است.'
            : 'Offline Mode: Internet is required to download Front Companies & Vessels from WikIran.org.',
        type: 'error',
      });
      return;
    }
    setBusyAction(`wikiran_sync_${target}`);
    setWikiranSyncNote(null);
    setBannerMessage(null);
    try {
      const res = await fetch('/api/wikiran/sync-archives', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target }),
      });
      const json = await res.json();
      await fetchOverview();
      if (json.ok) {
        const fc = Number(json.summary?.front_companies || 0);
        const vs = Number(json.summary?.vessels || 0);
        const added = Number(json.newly_added || 0);
        const msg =
          lang === 'fa'
            ? `همگام‌سازی کامل شد: ${fc.toLocaleString()} شرکت پوششی (Front Companies) و ${vs.toLocaleString()} کشتی (Vessels) اکنون به‌صورت ۱۰۰٪ آفلاین در جستجوی محلی ذخیره شدند (+${added.toLocaleString()} رکورد جدید).`
            : `Offline sync complete: ${fc.toLocaleString()} Front Companies & ${vs.toLocaleString()} Vessels are now indexed 100% offline in local SQLite FTS5 (+${added.toLocaleString()} newly added).`;
        setWikiranSyncNote(msg);
        setBannerMessage({ text: msg, type: 'info' });
      } else {
        setBannerMessage({
          text: json.error || 'WikIran structured archive sync failed.',
          type: 'error',
        });
      }
    } catch (err) {
      setBannerMessage({ text: `WikIran sync error: ${String(err)}`, type: 'error' });
    } finally {
      setBusyAction(null);
    }
  };

  const runUniversalSearchWithQuery = async (
    q: string,
    opts?: {
      category?: string;
      org?: string;
      type?: string;
      from?: string;
      to?: string;
      includeLive?: boolean;
      leakSource?: string;
    }
  ) => {
    setBusyAction('search');
    const targetCategory = opts?.category ?? filterCategory;
    const targetOrg = opts?.org ?? filterOrg;
    const targetType = opts?.type ?? filterType;
    const targetFrom = opts?.from ?? filterDateFrom;
    const targetTo = opts?.to ?? filterDateTo;
    const targetLive = (opts?.includeLive ?? includeLiveWikIran) && !isOffline;
    const targetLeakSource = opts?.leakSource !== undefined ? opts.leakSource : activeLeakSourceFilter;

    try {
      const res = await fetch('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: q,
          category_slug: targetCategory === 'ALL' ? null : targetCategory,
          organization_name: targetOrg === 'ALL' ? null : targetOrg,
          source_type: targetType === 'ALL' ? null : targetType,
          date_from: targetFrom || null,
          date_to: targetTo || null,
          include_live_wikiran: targetLive,
          leak_source: targetLeakSource || null,
          live_pages: 2,
        }),
      });
      const json = await res.json();
      if (json.ok) {
        setSearchResults(json.results);
        setWikiranLiveMeta(json.wikiran_live || null);
      }
    } catch {
      // Offline fallback over cached local SQLite records if browser network is completely severed
      if (data) {
        const needle = q.trim().toLowerCase();
        const localPool: Array<Record<string, unknown>> = [
          ...data.articles.map((a) => ({
            record_type: 'ARTICLE',
            id: a.id,
            title: a.title,
            short_description: a.summary,
            matched_excerpt: a.editorial_content,
            publication_date: a.publication_date,
            category_en: a.categories_en,
            category_fa: a.categories_fa,
            organizations: a.organizations_list,
            source_url: a.source_url,
            extraction_status: a.extraction_status,
            record_version: a.record_version,
          })),
          ...data.publications.map((p) => ({
            record_type: 'PUBLICATION',
            id: p.id,
            title: p.title,
            short_description: p.description,
            matched_excerpt: p.description,
            publication_date: p.publication_date,
            category_en: p.categories_en,
            category_fa: p.categories_fa,
            organizations: '',
            source_url: p.source_url,
            extraction_status: p.extraction_status,
            record_version: p.record_version,
          })),
          ...(currentCsvRows || []).map((r) => ({
            record_type: 'CSV_ROW',
            id: r.id,
            title: `${currentCsvDataset?.dataset_name || 'CSV'} — Row #${r.row_number}`,
            short_description: r.searchable_text,
            matched_excerpt: r.searchable_text,
            publication_date: '2026-01-01',
            category_en: 'Spreadsheet / CSV Data',
            category_fa: 'داده جدولی اکسل / CSV',
            organizations: '',
            source_url: `local://csv/${currentCsvDataset?.original_filename || 'table.csv'}#row-${r.row_number}`,
            extraction_status: 'INDEXED',
            record_version: 1,
          })),
        ];
        const filtered = localPool.filter((item) => {
          if (targetType !== 'ALL' && item.record_type !== targetType) return false;
          if (targetFrom || targetTo) {
            const pubD = String(item.publication_date || '').trim().slice(0, 10);
            if (!pubD) return false;
            if (targetFrom && pubD < targetFrom) return false;
            if (targetTo && pubD > targetTo) return false;
          }
          if (!needle) return true;
          const haystack = `${item.title} ${item.short_description} ${item.matched_excerpt} ${item.organizations} ${item.source_url}`.toLowerCase();
          return haystack.includes(needle);
        });
        setSearchResults(filtered);
      }
    } finally {
      setBusyAction(null);
    }
  };

  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setSearchScopeTab('ALL');
    await runUniversalSearchWithQuery(searchQuery);
  };

  const handleOfacSync = async (opts: { force?: boolean; check_only?: boolean } = {}) => {
    if (isOffline) {
      setBannerMessage({
        text:
          lang === 'fa'
            ? 'آفلاین: اتصال به اینترنت برای همگام‌سازی اوفک (OFAC) برقرار نیست، اما جستجوی آفلاین در کل رکوردهای اوفک ذخیره‌شده کاملاً فعال است.'
            : 'Offline Mode: Internet is needed to check U.S. Treasury SLS for updates, but offline screening across all locally saved OFAC sanctions records remains 100% active.',
        type: 'error',
      });
      return;
    }
    setBusyAction(opts.check_only ? 'ofac_check' : 'ofac_sync');
    setOfacStatusNote(null);
    try {
      const res = await fetch('/api/ofac/sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(opts),
      });
      const json = await res.json();
      if (json.ok) {
        if (json.action === 'CHECK_ONLY') {
          const msg = json.update_available
            ? lang === 'fa'
              ? `نسخه جدید اوفک (OFAC Publication #${json.latest_publication_id}) آماده دانلود است! برای دریافت کل دیتاست روی دکمه همگام‌سازی کلیک کنید.`
              : `New OFAC update available! U.S. Treasury Publication #${json.latest_publication_id} (${String(json.latest_date_published || '').slice(0, 10)}) is ready to download.`
            : lang === 'fa'
            ? `دیتاست آفلاین اوفک شما کاملاً به‌روز است (Publication #${json.latest_publication_id} · ${Number(json.local_entities_count || 0).toLocaleString()} رکورد).`
            : `Your offline OFAC dataset is up to date (U.S. Treasury Publication #${json.latest_publication_id} · ${Number(json.local_entities_count || 0).toLocaleString()} entities).`;
          setOfacStatusNote(msg);
          setBannerMessage({ text: msg, type: 'info' });
        } else if (json.action === 'UP_TO_DATE') {
          const msg =
            lang === 'fa'
              ? `دیتاست اوفک پیش‌تر با آخرین نسخه (#${json.latest_publication_id}) همگام‌سازی شده است.`
              : `OFAC dataset already matches the latest U.S. Treasury Publication #${json.latest_publication_id}.`;
          setOfacStatusNote(msg);
          setBannerMessage({ text: msg, type: 'info' });
        } else {
          const count = Number(json.synced_count || json.summary?.total_entities || 0);
          const msg =
            lang === 'fa'
              ? `همگام‌سازی کامل اوفک (OFAC) انجام شد: ${count.toLocaleString()} نهاد و فرد تحریمی (SDN + Non-SDN Consolidated · نسخه #${json.publication_id}) در دیتابیس محلی SQLite و جستجوی FTS5 ذخیره شدند.`
              : `OFAC Super-Dataset synced: ${count.toLocaleString()} official SDN & Non-SDN Consolidated entities (Publication #${json.publication_id}) downloaded and indexed offline in SQLite FTS5.`;
          setOfacStatusNote(msg);
          setBannerMessage({ text: msg, type: 'info' });
          await fetchOverview();
        }
      } else {
        setBannerMessage({
          text: json.error || 'OFAC sync failed. Please check network connectivity to sanctionslistservice.ofac.treas.gov.',
          type: 'error',
        });
      }
    } catch (err) {
      setBannerMessage({ text: `OFAC sync error: ${String(err)}`, type: 'error' });
    } finally {
      setBusyAction(null);
    }
  };

  const handleOpenSanctionsSync = async (
    opts: { force?: boolean; check_only?: boolean; dataset?: string } = {}
  ) => {
    if (isOffline) {
      setBannerMessage({
        text:
          lang === 'fa'
            ? 'آفلاین: برای بررسی و دانلود OpenSanctions اینترنت لازم است، اما جستجوی آفلاین در رکوردهای ذخیره‌شده فعال است.'
            : 'Offline Mode: Internet is needed to check OpenSanctions index.json for updates, while local offline screening remains 100% active.',
        type: 'error',
      });
      return;
    }
    setBusyAction(opts.check_only ? 'os_check' : 'os_sync');
    setOsStatusNote(null);
    try {
      const res = await fetch('/api/opensanctions/sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dataset: 'sanctions', ...opts }),
      });
      const json = await res.json();
      if (json.ok) {
        const msg =
          json.message ||
          (lang === 'fa'
            ? `همگام‌سازی OpenSanctions با موفقیت انجام شد (${Number(json.summary?.total_entities || 0).toLocaleString()} رکورد).`
            : `OpenSanctions synced (${Number(json.summary?.total_entities || 0).toLocaleString()} global targets offline).`);
        setOsStatusNote(msg);
        setBannerMessage({ text: msg, type: 'info' });
        await fetchOverview();
      } else {
        setBannerMessage({
          text: json.error || 'OpenSanctions sync failed.',
          type: 'error',
        });
      }
    } catch (err) {
      setBannerMessage({ text: `OpenSanctions sync error: ${String(err)}`, type: 'error' });
    } finally {
      setBusyAction(null);
    }
  };

  const handleFullBackupRestoreUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;
    setBusyAction('full_restore');
    setFullBackupMsg(null);
    try {
      const res = await fetch('/api/backup/full-restore-upload', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/octet-stream',
          'X-Backup-Filename': file.name,
        },
        body: file,
      });
      const json = await res.json();
      if (json.ok) {
        const rawRestored = Number(json.restore?.restored_raw_files || 0);
        const msg =
          lang === 'fa'
            ? `بازیابی کامل بکاپ (${file.name}) با موفقیت انجام شد! کل دیتابیس (ویکی‌ایران + اوفک + OpenSanctions) و ${rawRestored} فایل خام بدون نیاز به دانلود مجدد بازیابی شدند.`
            : `Full Portable Backup (${file.name}) restored cleanly! Complete database (WikIran + OFAC + OpenSanctions) and ${rawRestored} raw dataset files are now active offline.`;
        setFullBackupMsg(msg);
        setBannerMessage({ text: msg, type: 'info' });
        await fetchOverview();
      } else {
        setBannerMessage({
          text: json.error || 'Could not restore uploaded backup file.',
          type: 'error',
        });
      }
    } catch (err) {
      setBannerMessage({ text: `Restore upload error: ${String(err)}`, type: 'error' });
    } finally {
      setBusyAction(null);
    }
  };

  const handleUpdateArchive = async (
    simulateInterruptAfter?: number,
    maxItems: number = 25,
    deepSpider: boolean = true,
    mode: 'discover' | 'deep_spider' | 'check_updates' | 'incremental' = 'incremental'
  ) => {
    if (isOffline) {
      setBannerMessage({
        text:
          lang === 'fa'
            ? 'آفلاین (Disconnected): اتصال به اینترنت برقرار نیست. دریافت داده جدید از سرور متوقف است، اما جستجو، مرور و خروجی اکسل از دیتابیس محلی SQLite کاملاً فعال است.'
            : 'Disconnected (Offline Mode): Remote server sync requires internet, but all local SQLite search, browsing, and Excel exports remain 100% functional.',
        type: 'error',
      });
      return;
    }
    const modeTitle =
      mode === 'discover'
        ? lang === 'fa'
          ? 'کشف مسیرهای جدید (Discovery Frontier Scan)'
          : 'Discover New Paths (Sitemap, Documents & Deep Leak Pages)'
        : mode === 'deep_spider'
        ? lang === 'fa'
          ? 'خزش عنکبوتی عمیق (Deep Spider — فقط مسیرهای جدید)'
          : 'Deep Spider Crawl (Unseen Frontier Paths to End)'
        : mode === 'check_updates'
        ? lang === 'fa'
          ? 'بررسی آپدیت مسیرهای قبلی (Check Updates)'
          : 'Check Updates (Verify Older & Recent Paths)'
        : lang === 'fa'
        ? 'بررسی و دریافت بروزرسانی‌های سرور (Lookup Server)'
        : 'Server Lookup & Incremental Spider';

    setCrawlModeLabel(modeTitle);
    setBusyAction('update');
    setBannerMessage(null);
    try {
      const res = await fetch('/api/update-archive', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mode: mode === 'incremental' ? undefined : mode,
          max_items: maxItems,
          deep_spider: deepSpider,
          simulate_interrupt_after: simulateInterruptAfter,
        }),
      });
      const json = await res.json();
      await fetchOverview();
      if (json.ok && json.job) {
        const status = json.job.status;
        const newCount = json.job.new_records_count ?? 0;
        const updCount = json.job.updated_records_count ?? 0;
        const procCount = json.job.processed_count ?? 0;
        const discCount = json.job.total_discovered ?? procCount;
        const pendingFrontier = json.frontier_stats?.pending ?? 0;
        if (status === 'FAILED' || status === 'SUSPENDED') {
          setBannerMessage({
            text:
              lang === 'fa'
                ? `خطا در عملیات (${status}): ${json.job.error_summary || 'خطای شبکه'}`
                : `Crawler ${status.toLowerCase()}: ${json.job.error_summary || 'Network error'}`,
            type: 'error',
          });
        } else if (status === 'INTERRUPTED') {
          setBannerMessage({
            text:
              lang === 'fa'
                ? `عملیات توسط کاربر متوقف شد (Job #${json.job.id} — ${newCount} مورد جدید ذخیره شد، ${pendingFrontier} مسیر جدید در صف خزش باقی مانده است).`
                : `Operation stopped cleanly by user (Job #${json.job.id} — ${newCount} new saved, ${pendingFrontier} unseen paths queued in frontier).`,
            type: 'info',
          });
        } else if (mode === 'discover') {
          setBannerMessage({
            text:
              lang === 'fa'
                ? `کشف مسیرهای جدید کامل شد: ${newCount} لینک جدید کشف و در صف قرار گرفت (مجموع مسیرهای آماده خزش: ${pendingFrontier}). حالا روی «Deep Spider» کلیک کنید.`
                : `Discovery complete: ${newCount} brand-new unseen path(s) queued across ${procCount} hub/leak pages (${pendingFrontier} pending in frontier). Click "Deep Spider" to extract them.`,
            type: 'info',
          });
        } else if (mode === 'check_updates') {
          setBannerMessage({
            text:
              lang === 'fa'
                ? `بررسی آپدیت مسیرهای قبلی کامل شد: ${procCount} مسیر بررسی شد (${newCount} مورد جدید، ${updCount} مورد تغییر یافته).`
                : `Update Check complete: verified ${procCount} recent & older archived paths (${newCount} new, ${updCount} updated).`,
            type: 'info',
          });
        } else {
          setBannerMessage({
            text:
              lang === 'fa'
                ? `خزش عمیق (Deep Spider) کامل شد: ${newCount} رکورد جدید دانلود و ذخیره شد، ${updCount} مورد بروزرسانی شد (${procCount} از ${discCount} مسیر بررسی شد · ${pendingFrontier} مسیر جدید دیگر در صف).`
                : `Deep Spider crawl complete: ${newCount} NEW records extracted & indexed, ${updCount} updated (${procCount}/${discCount} paths processed · ${pendingFrontier} unseen paths remaining in frontier).`,
            type: 'info',
          });
        }
      }
    } finally {
      setBusyAction(null);
    }
  };

  const handleSaveSchedule = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusyAction('schedule-save');
    try {
      const res = await fetch('/api/schedule', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          enabled: schedEnabled,
          frequency: schedFreq,
          time_utc: schedTime,
          day_of_week: schedDay,
          max_items_per_run: schedMaxItems,
        }),
      });
      const json = await res.json();
      await fetchOverview();
      if (json.ok) {
        setBannerMessage({
          text:
            lang === 'fa'
              ? `تنظیمات زمان‌بندی خودکار ذخیره شد. اجرای بعدی: ${json.schedule.next_run_at}`
              : `Scheduled Collection updated. Next background run: ${json.schedule.next_run_at}`,
          type: 'info',
        });
      }
    } finally {
      setBusyAction(null);
    }
  };

  const handleTriggerScheduledRunNow = async () => {
    setBusyAction('schedule-run');
    try {
      const res = await fetch('/api/schedule/run-now', { method: 'POST' });
      const json = await res.json();
      await fetchOverview();
      if (json.ok) {
        setBannerMessage({
          text:
            lang === 'fa'
              ? `سرویس زمان‌بندی پس‌زمینه اجرا شد (Job #${json.job?.id}).`
              : `Background scheduled task executed (Job #${json.job?.id}).`,
          type: 'info',
        });
      }
    } finally {
      setBusyAction(null);
    }
  };

  const handleCsvFilterChange = async (
    datasetId: number | null,
    query: string,
    previewAllFlag: boolean = csvPreviewAll,
    crossAuditFlag: boolean = csvCrossDatasetAudit
  ) => {
    setCsvFilterQuery(query);
    setSelectedCsvId(datasetId);
    setCsvPreviewAll(previewAllFlag);
    setCsvCrossDatasetAudit(crossAuditFlag);
    const res = await fetch('/api/csv/view', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        dataset_id: datasetId,
        query,
        preview_all: previewAllFlag,
        cross_dataset_audit: crossAuditFlag,
      }),
    });
    const json = await res.json();
    if (json.ok) {
      setActiveCsvView(json.active_csv);
    }
  };

  const handleCsvFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusyAction('csv-upload');
    try {
      const text = await file.text();
      const res = await fetch('/api/csv/import', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          csv_text: text,
          filename: file.name,
          dataset_name: file.name.replace(/\.csv$/i, ''),
        }),
      });
      const json = await res.json();
      await fetchOverview();
      if (json.ok && json.active_csv?.dataset) {
        setActiveCsvView(json.active_csv);
        setSelectedCsvId(json.active_csv.dataset.id);
        setCsvPreviewAll(true);
        setBannerMessage({
          text:
            lang === 'fa'
              ? `فایل CSV «${file.name}» با موفقیت به جدول اکسل (.xlsx) تبدیل شد و تمام ردیف‌های آن در موتور جستجوی جامع ثبت گردید.`
              : `CSV "${file.name}" converted to Excel (.xlsx) and indexed for universal search.`,
          type: 'info',
        });
      }
    } finally {
      setBusyAction(null);
      e.target.value = '';
    }
  };

  const handleResumeJob = async (jobId: number) => {
    setBusyAction(`resume-${jobId}`);
    try {
      const res = await fetch('/api/resume-job', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_id: jobId }),
      });
      const json = await res.json();
      await fetchOverview();
      if (json.ok) {
        setBannerMessage({
          text:
            lang === 'fa'
              ? `ادامه عملیات دریافت (#${jobId}) با موفقیت از نقطه ذخیره تکمیل شد.`
              : `Interrupted collection job #${jobId} resumed from checkpoint and completed.`,
          type: 'info',
        });
      }
    } finally {
      setBusyAction(null);
    }
  };

  const handleCreateBackup = async () => {
    setBusyAction('backup');
    try {
      const res = await fetch('/api/backup/create', { method: 'POST' });
      const json = await res.json();
      await fetchOverview();
      if (json.ok) {
        setBannerMessage({ text: json.clerk_message, type: 'info' });
      }
    } finally {
      setBusyAction(null);
    }
  };

  const handleConfirmRestore = async (backupPath: string) => {
    setBusyAction('restore');
    try {
      const res = await fetch('/api/backup/restore', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: backupPath, confirmed: true }),
      });
      const json = await res.json();
      setConfirmRestorePath(null);
      await fetchOverview();
      if (json.ok) {
        setBannerMessage({ text: json.clerk_message, type: 'info' });
      }
    } finally {
      setBusyAction(null);
    }
  };

  const handleRunTests = async () => {
    setBusyAction('tests');
    try {
      const res = await fetch('/api/tests');
      const json = await res.json();
      setTestOutput(json.output);
    } finally {
      setBusyAction(null);
    }
  };

  const handleRunRecon = async () => {
    setBusyAction('recon');
    try {
      const res = await fetch('/api/reconnaissance', { method: 'POST' });
      const json = await res.json();
      if (json.ok && json.markdown) {
        setDocKey('reconnaissance');
        setDocContent({ filename: 'RECONNAISSANCE_REPORT.md (Live Run)', content: json.markdown });
        setBannerMessage({
          text:
            lang === 'fa'
              ? 'شناسایی فنی وب‌سایت و بررسی مسیرهای مجاز با موفقیت انجام شد.'
              : 'Live website reconnaissance and permitted path analysis completed.',
          type: 'info',
        });
      }
    } finally {
      setBusyAction(null);
    }
  };

  // Streamlined 3-Group Sidebar Navigation:
  // 1) Core Daily Workspace (Dashboard, Search & Screen, Export & Converter)
  // 2) Optional Archive Reference Tables (Articles, Catalogue, Organizations, Categories — collapsed by default)
  // 3) System & Updates (History, Settings, Help)
  const coreNavItems: Array<{
    id: NavSection;
    label: string;
    icon: React.ReactNode;
    activeClass: string;
    dotClass: string;
  }> = [
    {
      id: 'dashboard',
      label: t.nav_dashboard,
      icon: <LayoutDashboard className="w-4 h-4 text-sky-400 shrink-0" />,
      activeClass: 'bg-sky-600 text-white shadow-xs',
      dotClass: 'bg-sky-400',
    },
    {
      id: 'search',
      label: lang === 'fa' ? 'جستجو و استعلام (OFAC + ویکی‌ایران)' : 'Search & Screen',
      icon: <Search className="w-4 h-4 text-indigo-400 shrink-0" />,
      activeClass: 'bg-indigo-600 text-white shadow-xs',
      dotClass: 'bg-indigo-400',
    },
    {
      id: 'watchlist',
      label: lang === 'fa' ? 'غربالگری گروهی (Excel/CSV)' : 'Batch Watchlist Screener',
      icon: <ClipboardList className="w-4 h-4 text-rose-400 shrink-0" />,
      activeClass: 'bg-rose-600 text-white shadow-xs',
      dotClass: 'bg-rose-400',
    },
    {
      id: 'targeted_leaks',
      label: lang === 'fa' ? 'دانلود هدفمند افشاگری‌ها' : 'Targeted Leak Downloader',
      icon: <HardDriveDownload className="w-4 h-4 text-cyan-400 shrink-0" />,
      activeClass: 'bg-cyan-600 text-white shadow-xs',
      dotClass: 'bg-cyan-400',
    },
    {
      id: 'exports',
      label: lang === 'fa' ? 'خروجی اکسل و مبدل خوانا' : 'Export & Data Converter',
      icon: <FileSpreadsheet className="w-4 h-4 text-emerald-400 shrink-0" />,
      activeClass: 'bg-emerald-600 text-white shadow-xs',
      dotClass: 'bg-emerald-400',
    },
  ];

  const referenceTableNavItems: Array<{
    id: NavSection;
    label: string;
    icon: React.ReactNode;
    activeClass: string;
    dotClass: string;
  }> = [
    {
      id: 'articles',
      label: t.nav_articles,
      icon: <BookOpen className="w-4 h-4 text-blue-400 shrink-0" />,
      activeClass: 'bg-blue-600 text-white shadow-xs',
      dotClass: 'bg-blue-400',
    },
    {
      id: 'publications',
      label: t.nav_publications,
      icon: <FolderKanban className="w-4 h-4 text-teal-400 shrink-0" />,
      activeClass: 'bg-teal-600 text-white shadow-xs',
      dotClass: 'bg-teal-400',
    },
    {
      id: 'organizations',
      label: t.nav_organizations,
      icon: <Building2 className="w-4 h-4 text-amber-400 shrink-0" />,
      activeClass: 'bg-amber-600 text-white shadow-xs',
      dotClass: 'bg-amber-400',
    },
    {
      id: 'categories',
      label: t.nav_categories,
      icon: <Tags className="w-4 h-4 text-purple-400 shrink-0" />,
      activeClass: 'bg-purple-600 text-white shadow-xs',
      dotClass: 'bg-purple-400',
    },
  ];

  const adminNavItems: Array<{
    id: NavSection;
    label: string;
    icon: React.ReactNode;
    activeClass: string;
    dotClass: string;
  }> = [
    {
      id: 'history',
      label: t.nav_history,
      icon: <History className="w-4 h-4 text-orange-400 shrink-0" />,
      activeClass: 'bg-orange-600 text-white shadow-xs',
      dotClass: 'bg-orange-400',
    },
    {
      id: 'settings',
      label: t.nav_settings,
      icon: <Settings className="w-4 h-4 text-cyan-400 shrink-0" />,
      activeClass: 'bg-cyan-700 text-white shadow-xs',
      dotClass: 'bg-cyan-400',
    },
    {
      id: 'help',
      label: t.nav_help,
      icon: <HelpCircle className="w-4 h-4 text-rose-400 shrink-0" />,
      activeClass: 'bg-rose-600 text-white shadow-xs',
      dotClass: 'bg-rose-400',
    },
  ];

  const allNavItems = [...coreNavItems, ...referenceTableNavItems, ...adminNavItems];

  if (loading || !data) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6">
        <div className="max-w-md w-full bg-white border border-slate-200 rounded-lg p-6 text-center space-y-3">
          <RefreshCw className="w-6 h-6 text-indigo-600 animate-spin mx-auto" />
          <div className="text-base font-semibold text-slate-900">
            Initializing WikIran Archive (SQLite + FTS5)...
          </div>
          <p className="text-xs text-slate-500">
            Verifying normalized SQLite schema, universal FTS5 search index, and CSV-to-Excel workbench.
          </p>
        </div>
      </div>
    );
  }

  const isFullUnredactedMode = data.settings?.strict_sensitive_exclusion === 'false';

  const displayedSearchResults = (
    searchResults !== null
      ? searchResults
      : [
          ...data.articles.map((a) => ({
            record_type: 'ARTICLE',
            id: a.id,
            title: a.title,
            short_description: a.summary,
            publication_date: a.publication_date,
            category_en: a.categories_en,
            category_fa: a.categories_fa,
            organizations: a.organizations_list,
            source_url: a.source_url,
            extraction_status: a.extraction_status,
            record_version: a.record_version,
          })),
          ...data.publications.map((p) => ({
            record_type: 'PUBLICATION',
            id: p.id,
            title: p.title,
            short_description: p.description,
            publication_date: p.publication_date,
            category_en: p.categories_en,
            category_fa: p.categories_fa,
            organizations: '',
            source_url: p.source_url,
            extraction_status: p.extraction_status,
            record_version: p.record_version,
          })),
        ]
  ).filter((row) => {
    if (!filterDateFrom && !filterDateTo) return true;
    const pubD = String(row.publication_date || '').trim().slice(0, 10);
    if (!pubD) return false;
    if (filterDateFrom && pubD < filterDateFrom) return false;
    if (filterDateTo && pubD > filterDateTo) return false;
    return true;
  });

  const currentCsvState = activeCsvView ?? data.active_csv;
  const currentCsvDataset = currentCsvState?.dataset ?? null;
  const currentCsvRows = currentCsvState?.rows ?? [];
  const totalCsvMatching = currentCsvState?.total_matching_count ?? currentCsvRows.length;
  const displayedCsvCount = currentCsvState?.displayed_count ?? currentCsvRows.length;
  const isCsvSubset = Boolean(currentCsvState?.is_subset);

  return (
    <div dir={isRtl ? 'rtl' : 'ltr'} className="min-h-screen bg-slate-50 text-slate-900 flex relative">
      {/* APPLICATION WORKFLOW MODAL (Triggers on first launch & via "How to work?" button) */}
      {showWorkflowModal && (
        <div
          className="fixed inset-0 z-50 bg-slate-950/70 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto"
          role="dialog"
          aria-modal="true"
        >
          <div className="bg-white border-2 border-indigo-300 rounded-xl max-w-4xl w-full overflow-hidden shadow-xl my-auto">
            <div className="bg-slate-900 text-white px-6 py-5 flex items-start justify-between gap-4 border-b border-slate-800">
              <div className="space-y-1">
                <div className="text-xs font-bold text-sky-400 uppercase tracking-wider">
                  {lang === 'fa' ? 'راهنمای شروع سریع (گام‌به‌گام)' : 'QUICK START WALKTHROUGH · STEP-BY-STEP GUIDE'}
                </div>
                <h2 className="text-lg sm:text-xl font-bold text-white">
                  {t.workflowModalTitle}
                </h2>
                <p className="text-xs text-slate-300 max-w-2xl leading-relaxed">
                  {t.workflowModalSubtitle}
                </p>
              </div>
              <button
                onClick={closeWorkflowModal}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer shrink-0"
                aria-label="Close modal"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-4 bg-slate-50">
              {/* Walkthrough Step 1: Update Archive (Admin) */}
              <div className="bg-white border border-sky-200 border-t-4 border-t-sky-600 rounded-lg p-5 flex flex-col justify-between space-y-4">
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold px-2 py-0.5 rounded bg-sky-100 text-sky-900">
                      {t.workflowStep1Badge}
                    </span>
                    <RefreshCw className="w-4 h-4 text-sky-700" />
                  </div>
                  <h3 className="text-sm font-bold text-slate-900">{t.workflowStep1Title}</h3>
                  <p className="text-xs text-slate-600 leading-relaxed">{t.workflowStep1Desc}</p>
                </div>
                <button
                  onClick={() => {
                    closeWorkflowModal();
                    handleUpdateArchive();
                  }}
                  className="w-full py-2 px-3 text-xs font-semibold text-white bg-sky-700 hover:bg-sky-800 rounded-md transition-colors cursor-pointer"
                >
                  {t.workflowStep1Btn}
                </button>
              </div>

              {/* Walkthrough Step 2: Search All Downloaded Data (Clerk) */}
              <div className="bg-white border border-indigo-200 border-t-4 border-t-indigo-600 rounded-lg p-5 flex flex-col justify-between space-y-4">
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold px-2 py-0.5 rounded bg-indigo-100 text-indigo-900">
                      {t.workflowStep2Badge}
                    </span>
                    <Search className="w-4 h-4 text-indigo-700" />
                  </div>
                  <h3 className="text-sm font-bold text-slate-900">{t.workflowStep2Title}</h3>
                  <p className="text-xs text-slate-600 leading-relaxed">{t.workflowStep2Desc}</p>
                </div>
                <button
                  onClick={() => {
                    closeWorkflowModal();
                    setActiveNav('search');
                  }}
                  className="w-full py-2 px-3 text-xs font-semibold text-white bg-indigo-700 hover:bg-indigo-800 rounded-md transition-colors cursor-pointer"
                >
                  {t.workflowStep2Btn}
                </button>
              </div>

              {/* Walkthrough Step 3: Export & CSV-to-Excel (Clerk) */}
              <div className="bg-white border border-emerald-200 border-t-4 border-t-emerald-600 rounded-lg p-5 flex flex-col justify-between space-y-4">
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold px-2 py-0.5 rounded bg-emerald-100 text-emerald-900">
                      {t.workflowStep3Badge}
                    </span>
                    <FileSpreadsheet className="w-4 h-4 text-emerald-700" />
                  </div>
                  <h3 className="text-sm font-bold text-slate-900">{t.workflowStep3Title}</h3>
                  <p className="text-xs text-slate-600 leading-relaxed">{t.workflowStep3Desc}</p>
                </div>
                <button
                  onClick={() => {
                    closeWorkflowModal();
                    setActiveNav('exports');
                  }}
                  className="w-full py-2 px-3 text-xs font-semibold text-white bg-emerald-700 hover:bg-emerald-800 rounded-md transition-colors cursor-pointer"
                >
                  {t.workflowStep3Btn}
                </button>
              </div>

              {/* Walkthrough Step 4: Backup & Schedule (Admin) */}
              <div className="bg-white border border-amber-200 border-t-4 border-t-amber-600 rounded-lg p-5 flex flex-col justify-between space-y-4">
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold px-2 py-0.5 rounded bg-amber-100 text-amber-900">
                      {t.workflowStep4Badge}
                    </span>
                    <Clock className="w-4 h-4 text-amber-700" />
                  </div>
                  <h3 className="text-sm font-bold text-slate-900">{t.workflowStep4Title}</h3>
                  <p className="text-xs text-slate-600 leading-relaxed">{t.workflowStep4Desc}</p>
                </div>
                <button
                  onClick={() => {
                    closeWorkflowModal();
                    setActiveNav('settings');
                  }}
                  className="w-full py-2 px-3 text-xs font-semibold text-white bg-amber-700 hover:bg-amber-800 rounded-md transition-colors cursor-pointer"
                >
                  {t.workflowStep4Btn}
                </button>
              </div>
            </div>

            <div className="px-6 py-4 bg-white border-t border-slate-200 flex flex-wrap items-center justify-between gap-3">
              <div className="text-xs text-slate-600">
                {lang === 'fa'
                  ? 'هر زمان نیاز به راهنما داشتید، روی دکمه «چگونه کار می‌کند؟» در بالای پیشخوان کلیک کنید.'
                  : 'You can reopen this visual walkthrough anytime via the "How to work?" button on the Dashboard.'}
              </div>
              <button
                onClick={closeWorkflowModal}
                className="px-5 py-2 text-xs font-bold text-white bg-slate-900 hover:bg-slate-800 rounded-lg transition-colors cursor-pointer"
              >
                {t.workflowCloseBtn}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Mobile / Tablet Backdrop Overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-slate-950/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar Navigation (Responsive Drawer on small screens, Static 264px on lg+) */}
      <aside
        className={`fixed lg:static inset-y-0 ${
          isRtl ? 'right-0' : 'left-0'
        } z-40 w-64 bg-slate-900 text-slate-100 flex flex-col shrink-0 border-e border-slate-800 transition-transform duration-200 ease-in-out ${
          sidebarOpen
            ? 'translate-x-0'
            : isRtl
            ? 'translate-x-full lg:translate-x-0'
            : '-translate-x-full lg:translate-x-0'
        }`}
      >
        <div className="px-5 py-4 border-b border-slate-800 bg-slate-950/60 flex items-center justify-between gap-2">
          <div>
            <div className="text-base font-bold tracking-tight text-white whitespace-nowrap">
              {t.appTitle}
            </div>
            <div className="text-xs text-sky-400 mt-0.5 leading-snug font-medium">
              Windows 11 · SQLite FTS5
            </div>
          </div>
          <button
            onClick={() => setSidebarOpen(false)}
            className="lg:hidden p-1.5 rounded text-slate-400 hover:text-white hover:bg-slate-800"
            aria-label="Close navigation menu"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-4 overflow-y-auto">
          {/* Group 1: Core Daily Workspace (Dashboard, Search & Screen, Export & Converter) */}
          <div className="space-y-1">
            <div className="px-3 pb-1.5 text-[11px] font-bold uppercase tracking-wider text-emerald-400 flex items-center justify-between">
              <span>{lang === 'fa' ? 'میز کار روزانه (اصلی)' : 'Core Workspace'}</span>
            </div>
            {coreNavItems.map((item) => {
              const active = activeNav === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => {
                    setActiveNav(item.id);
                    setSidebarOpen(false);
                  }}
                  className={`w-full flex items-center justify-between gap-2 px-3 py-2.5 text-xs sm:text-sm font-semibold rounded-md transition-colors cursor-pointer ${
                    active
                      ? item.activeClass
                      : 'text-slate-200 hover:bg-slate-800/90 hover:text-white'
                  }`}
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    {item.icon}
                    <span className="truncate">{item.label}</span>
                  </div>
                  <span
                    className={`w-2 h-2 rounded-full shrink-0 ${
                      active ? 'bg-white' : item.dotClass
                    }`}
                  />
                </button>
              );
            })}
          </div>

          {/* Group 2: Separated Collapsible Reference Tables (Articles, Catalogue, Organizations, Categories) */}
          <div className="space-y-1 pt-2 border-t border-slate-800">
            <button
              type="button"
              onClick={() => setShowArchiveTablesNav((prev) => !prev)}
              className="w-full px-3 py-1.5 text-[11px] font-bold uppercase tracking-wider text-slate-400 hover:text-slate-200 flex items-center justify-between gap-2 rounded transition-colors cursor-pointer"
            >
              <span>
                {lang === 'fa' ? 'جداول مرجع آرشیو (اختیاری)' : 'Archive Tables (Optional)'}
              </span>
              {showArchiveTablesNav ? (
                <ChevronDown className="w-3.5 h-3.5 shrink-0" />
              ) : (
                <ChevronRight className="w-3.5 h-3.5 shrink-0" />
              )}
            </button>
            {(showArchiveTablesNav ||
              referenceTableNavItems.some((it) => it.id === activeNav)) && (
              <div className="space-y-1 pt-0.5">
                {referenceTableNavItems.map((item) => {
                  const active = activeNav === item.id;
                  return (
                    <button
                      key={item.id}
                      onClick={() => {
                        setActiveNav(item.id);
                        setSidebarOpen(false);
                      }}
                      className={`w-full flex items-center justify-between gap-2 px-3 py-2 text-xs font-medium rounded-md transition-colors cursor-pointer ${
                        active
                          ? item.activeClass
                          : 'text-slate-400 hover:bg-slate-800/90 hover:text-white'
                      }`}
                    >
                      <div className="flex items-center gap-2.5 min-w-0">
                        {item.icon}
                        <span className="truncate">{item.label}</span>
                      </div>
                      <span
                        className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                          active ? 'bg-white' : item.dotClass
                        }`}
                      />
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* Group 3: System, Sync & Settings */}
          <div className="space-y-1 pt-2 border-t border-slate-800">
            <div className="px-3 pb-1.5 text-[11px] font-bold uppercase tracking-wider text-amber-400 flex items-center justify-between">
              <span>{t.sidebarAdminGroup}</span>
            </div>
            {adminNavItems.map((item) => {
              const active = activeNav === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => {
                    setActiveNav(item.id);
                    setSidebarOpen(false);
                  }}
                  className={`w-full flex items-center justify-between gap-2 px-3 py-2 text-xs font-medium rounded-md transition-colors cursor-pointer ${
                    active
                      ? item.activeClass
                      : 'text-slate-300 hover:bg-slate-800/90 hover:text-white'
                  }`}
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    {item.icon}
                    <span className="truncate">{item.label}</span>
                  </div>
                  <span
                    className={`w-2 h-2 rounded-full shrink-0 ${
                      active ? 'bg-white' : item.dotClass
                    }`}
                  />
                </button>
              );
            })}
          </div>
        </nav>

        {/* Sidebar Footer: Archive Size & Volume + How to Work + Language Switch */}
        <div className="p-3.5 border-t border-slate-800 space-y-2.5 bg-slate-950/50">
          {(() => {
            const sv = liveCrawlStatus?.storage_volume || data.storage_volume;
            const totalRecords =
              sv?.total_records ??
              data.stats.articles_count +
                data.stats.publications_count +
                data.stats.organizations_count +
                data.stats.entities_count;
            const dbSizeLabel = sv?.db_size_label || '—';
            const totalSizeLabel = sv?.total_size_label || dbSizeLabel;
            const artCount = sv?.articles_count ?? data.stats.articles_count;
            const pubCount = sv?.publications_count ?? data.stats.publications_count;
            const ofacCount = sv?.ofac_entities_count ?? data.ofac_summary?.total_entities ?? 0;
            const osCount = sv?.opensanctions_count ?? data.opensanctions_summary?.total_entities ?? 0;
            const csvCount = sv?.csv_rows_count ?? 0;
            const dbSharePct =
              sv && sv.total_bytes > 0
                ? Math.min(100, Math.max(8, Math.round((sv.db_bytes / sv.total_bytes) * 100)))
                : 100;

            return (
              <div className="bg-slate-900/95 border border-slate-700/80 rounded-lg p-3 space-y-2 shadow-inner">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-sky-400">
                    <HardDrive className="w-3.5 h-3.5 shrink-0" />
                    <span>{lang === 'fa' ? 'حجم و اندازه داده‌ها' : 'Data Size & Volume'}</span>
                  </div>
                  {(isCrawlingNow || busyAction === 'ofac_sync' || busyAction === 'os_sync') && (
                    <span className="inline-flex items-center gap-1 text-[10px] font-bold text-emerald-300">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                      LIVE
                    </span>
                  )}
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div className="bg-slate-950/80 border border-slate-800 rounded-md px-2.5 py-1.5">
                    <div className="text-[10px] text-slate-400 leading-tight">
                      {lang === 'fa' ? 'حجم دیتابیس' : 'SQLite DB'}
                    </div>
                    <div className="text-sm font-bold font-mono-tabular text-white mt-0.5">
                      {dbSizeLabel}
                    </div>
                  </div>
                  <div className="bg-slate-950/80 border border-slate-800 rounded-md px-2.5 py-1.5">
                    <div className="text-[10px] text-slate-400 leading-tight">
                      {lang === 'fa' ? 'تعداد رکوردها' : 'Total Volume'}
                    </div>
                    <div className="text-sm font-bold font-mono-tabular text-emerald-300 mt-0.5">
                      {totalRecords.toLocaleString()}
                    </div>
                  </div>
                </div>

                <div className="space-y-1">
                  <div className="flex items-center justify-between text-[10px] text-slate-400">
                    <span>{lang === 'fa' ? 'کل فضای دیسک آرشیو' : 'Total Disk Footprint'}</span>
                    <span className="font-mono-tabular font-semibold text-slate-200">
                      {totalSizeLabel}
                    </span>
                  </div>
                  <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-sky-500 to-emerald-400 rounded-full transition-all duration-300"
                      style={{ width: `${dbSharePct}%` }}
                    />
                  </div>
                  <div className="text-[10px] font-mono-tabular text-slate-400 flex flex-wrap items-center justify-between gap-1 pt-0.5">
                    <span>
                      {lang === 'fa'
                        ? `${artCount} مقاله · ${pubCount} فهرست`
                        : `${artCount} Art · ${pubCount} Cat`}
                    </span>
                    <span className="flex items-center gap-1.5">
                      {ofacCount > 0 && (
                        <span className="text-rose-300 font-semibold">
                          {ofacCount.toLocaleString()} OFAC
                        </span>
                      )}
                      {osCount > 0 && (
                        <span className="text-amber-300 font-semibold">
                          {osCount.toLocaleString()} OS
                        </span>
                      )}
                      {ofacCount === 0 && osCount === 0 && csvCount > 0 && (
                        <span className="text-sky-300/90">
                          {lang === 'fa' ? `${csvCount} ردیف CSV` : `${csvCount} CSV`}
                        </span>
                      )}
                    </span>
                  </div>
                </div>
              </div>
            );
          })()}

          <button
            onClick={() => {
              setShowWorkflowModal(true);
              setSidebarOpen(false);
            }}
            className="w-full py-2 px-3 text-xs font-bold text-sky-950 bg-sky-400 hover:bg-sky-300 rounded-md transition-colors inline-flex items-center justify-center gap-1.5 cursor-pointer"
          >
            <HelpCircle className="w-3.5 h-3.5" />
            <span>{t.howToWorkBtn}</span>
          </button>

          <div className="flex items-center gap-1 p-1 bg-slate-800 rounded-md">
            <button
              onClick={() => handleLanguageSwitch('en')}
              className={`flex-1 py-1.5 px-2 text-xs font-semibold rounded transition-colors whitespace-nowrap cursor-pointer ${
                lang === 'en' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
              }`}
            >
              English (LTR)
            </button>
            <button
              onClick={() => handleLanguageSwitch('fa')}
              className={`flex-1 py-1.5 px-2 text-xs font-semibold rounded transition-colors whitespace-nowrap cursor-pointer ${
                lang === 'fa' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
              }`}
            >
              فارسی (RTL)
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content Area (Responsive width & padding) */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Bar Contract: Responsive Zone 1 Brand/Menu — Zone 2 Quick Universal Search — Zone 3 Primary CTA */}
        <header className="flex flex-wrap items-center justify-between gap-3 px-4 sm:px-6 lg:px-8 py-3.5 bg-white border-b border-slate-200">
          <div className="flex items-center gap-3 min-w-0">
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden p-2 rounded-md border border-slate-200 text-slate-700 hover:bg-slate-100 cursor-pointer"
              aria-label="Open navigation menu"
            >
              <Menu className="w-4 h-4" />
            </button>
            <div className="text-sm sm:text-base font-bold text-slate-900 truncate">
              {t.appTitle} — {allNavItems.find((n) => n.id === activeNav)?.label}
            </div>
          </div>

          {/* Global Universal Search Bar in Header */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              setActiveNav('search');
              runUniversalSearchWithQuery(searchQuery);
            }}
            className="flex items-center gap-2 flex-1 max-w-md min-w-[220px]"
          >
            <div className="relative flex-1">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder={
                  lang === 'fa'
                    ? 'جستجوی سریع در تمام داده‌های دانلودشده...'
                    : 'Quick search across all downloaded data...'
                }
                className="w-full px-3 py-1.5 text-xs bg-slate-50 border border-slate-300 rounded-md focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-600"
              />
            </div>
            <button
              type="submit"
              className="px-3 py-1.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-md transition-colors shrink-0 cursor-pointer"
            >
              {lang === 'fa' ? 'جستجو' : 'Search'}
            </button>
          </form>

          <div className="flex items-center gap-2 shrink-0">
            {/* Network Status Indicator (Turns Red when Offline + Clickable to test Offline Mode) */}
            <button
              type="button"
              onClick={() => setIsOffline((prev) => !prev)}
              title={
                lang === 'fa'
                  ? 'وضعیت اتصال شبکه (برای شبیه‌سازی حالت آفلاین کلیک کنید)'
                  : 'Network Status Indicator (Click to toggle Offline / Online simulation)'
              }
              className={`px-3 py-2 text-xs font-bold rounded-md border transition-colors whitespace-nowrap inline-flex items-center gap-1.5 cursor-pointer shadow-xs ${
                isOffline
                  ? 'bg-red-600 text-white border-red-700 hover:bg-red-700'
                  : 'bg-emerald-50 text-emerald-900 border-emerald-300 hover:bg-emerald-100'
              }`}
            >
              {isOffline ? (
                <>
                  <WifiOff className="w-3.5 h-3.5 text-white shrink-0" />
                  <span>
                    {lang === 'fa' ? 'آفلاین / قطع ارتباط (Disconnected)' : 'Disconnected (Offline)'}
                  </span>
                </>
              ) : (
                <>
                  <span className="w-2 h-2 rounded-full bg-emerald-600 shrink-0" />
                  <Wifi className="w-3.5 h-3.5 text-emerald-700 shrink-0" />
                  <span>{lang === 'fa' ? 'آنلاین (متصل)' : 'Online'}</span>
                </>
              )}
            </button>
            <button
              onClick={() => setShowWorkflowModal(true)}
              className="px-3 py-2 text-xs font-bold text-indigo-950 bg-indigo-100 border border-indigo-300 rounded-md hover:bg-indigo-200 transition-colors whitespace-nowrap inline-flex items-center gap-1.5 cursor-pointer"
            >
              <HelpCircle className="w-3.5 h-3.5 text-indigo-700" />
              <span>{t.howToWorkBtn}</span>
            </button>
            <a
              href="/api/export/xlsx"
              className="px-3.5 py-2 text-xs font-semibold text-white bg-emerald-700 rounded-md hover:bg-emerald-800 transition-colors whitespace-nowrap inline-flex items-center gap-1.5 shadow-xs"
            >
              <FileSpreadsheet className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">{t.actionExportExcel}</span>
            </a>
          </div>
        </header>

        {/* Disconnected Banner (Appears when App is Offline while Local SQLite Search, Browsing & Export remain 100% functional) */}
        {isOffline && (
          <div className="bg-red-600 text-white border-b border-red-700 px-4 sm:px-6 lg:px-8 py-2.5 flex flex-wrap items-center justify-between gap-3 text-xs shadow-xs">
            <div className="flex items-center gap-2.5 min-w-0 flex-1">
              <WifiOff className="w-4 h-4 text-white shrink-0" />
              <span className="font-bold">
                {lang === 'fa'
                  ? 'قطع ارتباط با شبکه (Disconnected) — حالت آفلاین فعال است: دریافت داده جدید از سرور متوقف است، اما تمام امکانات جستجوی محلی، مرور مقالات و خروجی‌های اکسل از دیتابیس محلی SQLite کاملاً فعال هستند.'
                  : 'Disconnected — Offline Mode Active: Internet connection is unavailable. Server sync is paused, while all local SQLite FTS5 search, browsing, CSV-to-Excel workbench, and Excel/CSV/JSON exports remain 100% functional.'}
              </span>
            </div>
            <button
              type="button"
              onClick={() => setIsOffline(false)}
              className="px-2.5 py-1 text-xs font-bold bg-white text-red-700 rounded hover:bg-red-50 transition-colors shrink-0 cursor-pointer"
            >
              {lang === 'fa' ? 'بازگشت به حالت آنلاین' : 'Reconnect Online'}
            </button>
          </div>
        )}

        {/* Configurable Archive Scope Banner (Full Unredacted Mode vs Filtered Mode) */}
        <div
          className={`border-b px-4 sm:px-6 lg:px-8 py-2.5 flex flex-wrap items-center justify-between gap-3 text-xs ${
            isFullUnredactedMode
              ? 'bg-indigo-50/90 border-indigo-200 text-indigo-950'
              : 'bg-amber-50/90 border-amber-200 text-amber-950'
          }`}
        >
          <div className="flex items-center gap-2 min-w-0 flex-1">
            {isFullUnredactedMode ? (
              <Unlock className="w-4 h-4 text-indigo-700 shrink-0" />
            ) : (
              <Lock className="w-4 h-4 text-amber-700 shrink-0" />
            )}
            <span className="font-medium">
              {isFullUnredactedMode ? t.unredactedNotice : t.safetyNotice}
            </span>
          </div>
          <div className="flex items-center gap-3 shrink-0">
            <button
              onClick={() => handleToggleArchiveScope(!isFullUnredactedMode)}
              disabled={busyAction === 'toggle-scope'}
              className={`px-3 py-1 rounded font-semibold transition-colors cursor-pointer ${
                isFullUnredactedMode
                  ? 'bg-white text-slate-700 border border-slate-300 hover:bg-slate-100'
                  : 'bg-indigo-700 text-white hover:bg-indigo-800'
              }`}
            >
              {isFullUnredactedMode ? t.switchToFilteredModeBtn : t.switchToFullModeBtn}
            </button>
          </div>
        </div>

        {/* Friendly Clerk Notification Banner */}
        {bannerMessage && (
          <div
            className={`px-4 sm:px-6 lg:px-8 py-3 border-b flex items-center justify-between gap-3 text-xs sm:text-sm ${
              bannerMessage.type === 'error'
                ? 'bg-red-50 border-red-200 text-red-900'
                : 'bg-emerald-50 border-emerald-200 text-emerald-900'
            }`}
          >
            <div className="flex items-center gap-2">
              {bannerMessage.type === 'error' ? (
                <AlertTriangle className="w-4 h-4 text-red-700 shrink-0" />
              ) : (
                <CheckCircle2 className="w-4 h-4 text-emerald-700 shrink-0" />
              )}
              <span className="font-medium">{bannerMessage.text}</span>
            </div>
            <button
              onClick={() => setBannerMessage(null)}
              className="text-xs underline font-semibold px-2 py-1 shrink-0 cursor-pointer"
            >
              {lang === 'fa' ? 'بستن' : 'Dismiss'}
            </button>
          </div>
        )}

        {/* Viewport Content (Responsive padding & container) */}
        <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto space-y-6 sm:space-y-8">
          {/* 1. DASHBOARD */}
          {activeNav === 'dashboard' && (
            <div className="space-y-6 sm:space-y-8">
              {/* HERO SECTION: HOW THIS APP WORKS + "How to work?" Modal Trigger */}
              <section className="bg-white border border-indigo-200 rounded-xl overflow-hidden shadow-xs">
                <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 px-5 sm:px-6 py-5 text-white flex flex-wrap items-center justify-between gap-4">
                  <div className="space-y-1">
                    <div className="text-xs font-semibold text-sky-400 tracking-wide">
                      {lang === 'fa'
                        ? 'شروع سریع و راهنمای عملیاتی گام‌به‌گام'
                        : 'START HERE · INTERACTIVE OPERATIONAL WORKFLOW'}
                    </div>
                    <h1 className="text-base sm:text-lg md:text-xl font-bold text-white">
                      {t.howItWorksTitle}
                    </h1>
                    <p className="text-xs text-slate-300 max-w-3xl">{t.howItWorksSubtitle}</p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2.5 shrink-0">
                    <button
                      onClick={() => setShowWorkflowModal(true)}
                      className="px-4 py-2.5 text-xs font-bold text-slate-950 bg-amber-400 hover:bg-amber-300 rounded-lg transition-colors inline-flex items-center gap-2 cursor-pointer"
                    >
                      <HelpCircle className="w-4 h-4" />
                      <span>{t.howToWorkBtn}</span>
                    </button>
                    <button
                      onClick={handleRunVisualPipeline}
                      disabled={busyAction === 'pipeline' || busyAction === 'update'}
                      className="px-4 py-2.5 text-xs font-semibold text-white bg-sky-600 hover:bg-sky-500 rounded-lg transition-colors inline-flex items-center gap-2 cursor-pointer disabled:opacity-60"
                    >
                      <Play className="w-4 h-4" />
                      <span>{t.pipelineRunBtn}</span>
                    </button>
                    {(busyAction === 'pipeline' || busyAction === 'update') && (
                      <button
                        type="button"
                        onClick={handleStopCrawl}
                        className="px-4 py-2.5 text-xs font-bold text-white bg-red-600 hover:bg-red-700 rounded-lg transition-colors inline-flex items-center gap-2 cursor-pointer shadow-xs"
                      >
                        <Square className="w-3.5 h-3.5 fill-current" />
                        <span>{lang === 'fa' ? 'توقف خزش (Stop)' : 'Stop Crawling'}</span>
                      </button>
                    )}
                  </div>
                </div>

                {pipelineLog && !isCrawlingNow && (
                  <div className="px-5 sm:px-6 py-3 bg-sky-50 border-b border-sky-200 text-xs font-semibold text-sky-950 flex flex-wrap items-center justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                      <span>{pipelineLog}</span>
                    </div>
                    <div className="flex items-center gap-3 shrink-0">
                      <span className="font-mono-tabular text-sky-800">
                        Step {activePipelineStep}/4
                      </span>
                      <button
                        type="button"
                        onClick={() => setPipelineLog(null)}
                        className="text-slate-500 hover:text-slate-800 cursor-pointer"
                        aria-label="Dismiss status"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                )}

                {/* POLISHED ACTIVE SPIDER MONITOR WITH CSS RADAR VISUAL INDICATOR & 4 CONTROLS */}
                {(() => {
                  const job = liveCrawlStatus?.active_job || data.stats.last_job;
                  const frontier = liveCrawlStatus?.frontier_stats || data.frontier_stats;
                  const isRunningJob = Boolean(isCrawlingNow || (job && job.status === 'RUNNING'));
                  const discovered = isRunningJob && job ? job.total_discovered : frontier?.total ?? 0;
                  const processed = isRunningJob && job ? job.processed_count : frontier?.crawled ?? 0;
                  const newRecs = isRunningJob && job ? job.new_records_count : 0;
                  const pendingFrontier = frontier?.pending ?? 0;
                  const pct =
                    isRunningJob && discovered > 0
                      ? Math.min(100, Math.round((processed / discovered) * 100))
                      : 0;

                  return (
                    <div className="p-4 sm:p-5 bg-slate-100/70 border-b border-slate-200">
                      <div
                        className={`rounded-xl bg-slate-950 text-slate-100 p-4 sm:p-5 space-y-4 transition-all ${
                          isRunningJob
                            ? 'border-2 border-emerald-400 shadow-lg ring-4 ring-emerald-500/15'
                            : 'border-2 border-slate-700 shadow-md'
                        }`}
                      >
                        {/* Top Bar: Animated CSS Radar + Title + Elapsed + 4 Action Buttons */}
                        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                          <div className="flex items-center gap-3.5 min-w-0">
                            {/* CSS-Animated Spider Radar Visual Indicator */}
                            <div className="relative w-14 h-14 shrink-0 flex items-center justify-center rounded-xl bg-slate-900 border border-slate-700/90 shadow-inner overflow-hidden">
                              <svg
                                viewBox="0 0 64 64"
                                className="w-12 h-12"
                                aria-hidden="true"
                              >
                                {/* Concentric Web Rings */}
                                <circle
                                  cx="32"
                                  cy="32"
                                  r="26"
                                  fill="none"
                                  stroke={isRunningJob ? '#10B981' : '#475569'}
                                  strokeWidth="1"
                                  strokeOpacity="0.35"
                                />
                                <circle
                                  cx="32"
                                  cy="32"
                                  r="17"
                                  fill="none"
                                  stroke={isRunningJob ? '#38BDF8' : '#475569'}
                                  strokeWidth="1"
                                  strokeDasharray="3 3"
                                  strokeOpacity="0.45"
                                />
                                <circle
                                  cx="32"
                                  cy="32"
                                  r="8"
                                  fill="none"
                                  stroke={isRunningJob ? '#10B981' : '#64748B'}
                                  strokeWidth="1"
                                  strokeOpacity="0.55"
                                />
                                {/* Web Spokes */}
                                <line x1="32" y1="6" x2="32" y2="58" stroke="#334155" strokeWidth="0.9" />
                                <line x1="6" y1="32" x2="58" y2="32" stroke="#334155" strokeWidth="0.9" />
                                <line x1="13" y1="13" x2="51" y2="51" stroke="#334155" strokeWidth="0.8" />
                                <line x1="51" y1="13" x2="13" y2="51" stroke="#334155" strokeWidth="0.8" />

                                {isRunningJob && (
                                  <>
                                    {/* Expanding Radar Pulses */}
                                    <circle
                                      cx="32"
                                      cy="32"
                                      r="20"
                                      fill="none"
                                      stroke="#34D399"
                                      strokeWidth="2"
                                      className="animate-spider-pulse-1"
                                    />
                                    <circle
                                      cx="32"
                                      cy="32"
                                      r="20"
                                      fill="none"
                                      stroke="#38BDF8"
                                      strokeWidth="1.5"
                                      className="animate-spider-pulse-2"
                                    />
                                    {/* Rotating Radar Sweep Wedge */}
                                    <g className="animate-spider-radar">
                                      <path
                                        d="M32 32 L32 6 A26 26 0 0 1 54.5 19 Z"
                                        fill="rgba(16, 185, 129, 0.28)"
                                      />
                                      <line
                                        x1="32"
                                        y1="32"
                                        x2="32"
                                        y2="6"
                                        stroke="#34D399"
                                        strokeWidth="2"
                                        strokeLinecap="round"
                                      />
                                    </g>
                                    {/* Pulsing Target Nodes on the Spider Web */}
                                    <circle cx="44" cy="19" r="2.6" fill="#34D399" className="animate-spider-node-a" />
                                    <circle cx="19" cy="41" r="2.4" fill="#38BDF8" className="animate-spider-node-b" />
                                    <circle cx="46" cy="43" r="2.2" fill="#FBBF24" className="animate-spider-node-c" />
                                  </>
                                )}
                                {/* Center Spider Core */}
                                <circle
                                  cx="32"
                                  cy="32"
                                  r="4.2"
                                  fill={isRunningJob ? '#10B981' : '#38BDF8'}
                                />
                              </svg>
                            </div>

                            <div className="min-w-0 space-y-1">
                              <div className="flex flex-wrap items-center gap-2">
                                <span
                                  className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-[11px] font-extrabold uppercase tracking-wider ${
                                    isRunningJob
                                      ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-400/50'
                                      : 'bg-slate-800 text-sky-300 border border-slate-600'
                                  }`}
                                >
                                  <span
                                    className={`w-2 h-2 rounded-full ${
                                      isRunningJob ? 'bg-emerald-400 animate-ping' : 'bg-sky-400'
                                    }`}
                                  />
                                  {isRunningJob
                                    ? lang === 'fa'
                                      ? 'خزنده زنده فعال است'
                                      : 'ACTIVE SPIDER RUNNING'
                                    : lang === 'fa'
                                    ? 'مانیتور خزنده آماده (Standby)'
                                    : 'ACTIVE SPIDER MONITOR · READY'}
                                </span>
                                {isRunningJob && (
                                  <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-700 font-mono-tabular text-xs font-bold text-sky-300">
                                    {String(Math.floor(crawlElapsedSec / 60)).padStart(2, '0')}:
                                    {String(crawlElapsedSec % 60).padStart(2, '0')}
                                  </span>
                                )}
                              </div>
                              <div className="text-sm sm:text-base font-bold text-white tracking-tight truncate">
                                {isRunningJob
                                  ? crawlModeLabel ||
                                    (lang === 'fa'
                                      ? 'خزش عمیق در wikiran.org'
                                      : 'Deep Spidering wikiran.org')
                                  : lang === 'fa'
                                  ? 'کنترل ۴گانه خزنده: کشف مسیر جدید · خزش عمیق · بررسی آپدیت · توقف'
                                  : '4-Mode Spider Engine: Discover New · Deep Crawl · Check Updates · Stop'}
                              </div>
                            </div>
                          </div>

                          {/* 4 Distinct Required Spider Buttons */}
                          <div className="flex flex-wrap items-center gap-2 shrink-0">
                            <button
                              type="button"
                              onClick={() => handleUpdateArchive(undefined, 25, true, 'discover')}
                              disabled={isRunningJob}
                              className="px-3.5 py-2 text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg transition-colors inline-flex items-center gap-1.5 cursor-pointer disabled:opacity-50 shadow-xs"
                              title={
                                lang === 'fa'
                                  ? 'اسکن عمیق نقشه سایت، اسناد و صفحات جدید لیک‌ها برای کشف مسیرهای دانلودنشده'
                                  : 'Scan sitemaps, documents & deep leak pagination to discover brand-new unseen paths'
                              }
                            >
                              <Search className="w-3.5 h-3.5 shrink-0" />
                              <span>{lang === 'fa' ? '۱. کشف مسیر جدید' : '1. Discover'}</span>
                            </button>

                            <button
                              type="button"
                              onClick={() => handleUpdateArchive(undefined, 120, true, 'deep_spider')}
                              disabled={isRunningJob}
                              className="px-3.5 py-2 text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-500 rounded-lg transition-colors inline-flex items-center gap-1.5 cursor-pointer disabled:opacity-50 shadow-xs"
                              title={
                                lang === 'fa'
                                  ? 'خزش عمیق تا انتهای مسیرهای جدید کشف‌شده بدون تکرار موارد قبلی'
                                  : 'Crawl deeply through unseen frontier paths & nested links without repeating archived items'
                              }
                            >
                              <Activity className="w-3.5 h-3.5 shrink-0" />
                              <span>{lang === 'fa' ? '۲. خزش عمیق (Spider)' : '2. Deep Spider'}</span>
                            </button>

                            <button
                              type="button"
                              onClick={() => handleUpdateArchive(undefined, 25, false, 'check_updates')}
                              disabled={isRunningJob}
                              className="px-3.5 py-2 text-xs font-bold text-white bg-sky-600 hover:bg-sky-500 rounded-lg transition-colors inline-flex items-center gap-1.5 cursor-pointer disabled:opacity-50 shadow-xs"
                              title={
                                lang === 'fa'
                                  ? 'فقط بررسی مسیرهای قدیمی و صفحه اول جهت یافتن تغییرات و آپدیت‌های جدید'
                                  : 'Only re-check older downloaded paths & front feeds for modified/new records'
                              }
                            >
                              <RefreshCw
                                className={`w-3.5 h-3.5 shrink-0 ${
                                  isRunningJob ? 'animate-spin' : ''
                                }`}
                              />
                              <span>{lang === 'fa' ? '۳. بررسی آپدیت' : '3. Check Updates'}</span>
                            </button>

                            <button
                              type="button"
                              onClick={handleStopCrawl}
                              disabled={!isRunningJob}
                              className={`px-3.5 py-2 text-xs font-bold rounded-lg transition-all inline-flex items-center gap-1.5 ${
                                isRunningJob
                                  ? 'bg-rose-600 hover:bg-rose-500 text-white cursor-pointer shadow-md ring-2 ring-rose-400/60'
                                  : 'bg-slate-800 text-slate-500 border border-slate-700 cursor-not-allowed'
                              }`}
                            >
                              <Square className="w-3 h-3 fill-current shrink-0" />
                              <span>{lang === 'fa' ? '۴. توقف (Stop)' : '4. Stop'}</span>
                            </button>
                          </div>
                        </div>

                        {/* Live Progress Bar with Animated Shimmer */}
                        {isRunningJob && (
                          <div className="relative w-full h-2.5 bg-slate-800 rounded-full overflow-hidden border border-slate-700">
                            {discovered > 0 ? (
                              <div
                                className="h-full bg-gradient-to-r from-indigo-500 via-sky-400 to-emerald-400 transition-all duration-500 relative overflow-hidden"
                                style={{ width: `${Math.max(10, pct)}%` }}
                              >
                                <div className="absolute inset-0 w-1/2 bg-white/30 blur-xs animate-spider-shimmer" />
                              </div>
                            ) : (
                              <div className="h-full w-2/5 bg-gradient-to-r from-indigo-500 via-sky-400 to-emerald-400 animate-spider-shimmer rounded-full" />
                            )}
                          </div>
                        )}

                        {/* High-Contrast Live Metrics Strip */}
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                          <div className="bg-slate-900/95 border border-slate-700/90 rounded-lg px-3.5 py-2.5">
                            <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                              {lang === 'fa' ? 'مسیرهای جدید در صف' : 'Unseen Frontier Queue'}
                            </div>
                            <div className="text-xl font-extrabold font-mono-tabular text-indigo-300 mt-1">
                              {pendingFrontier.toLocaleString()}
                            </div>
                          </div>

                          <div className="bg-slate-900/95 border border-slate-700/90 rounded-lg px-3.5 py-2.5">
                            <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                              {isRunningJob
                                ? lang === 'fa'
                                  ? 'صفحه پردازش‌شده'
                                  : 'Processed Now'
                                : lang === 'fa'
                                ? 'مسیرهای بررسی‌شده'
                                : 'Frontier Crawled'}
                            </div>
                            <div className="text-xl font-extrabold font-mono-tabular text-sky-300 mt-1">
                              {processed.toLocaleString()}
                              {isRunningJob && discovered > 0 ? ` / ${discovered}` : ''}
                            </div>
                          </div>

                          <div className="bg-slate-900/95 border border-slate-700/90 rounded-lg px-3.5 py-2.5">
                            <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                              {lang === 'fa' ? 'رکورد جدید ذخیره‌شده' : 'New Saved (Run)'}
                            </div>
                            <div className="text-xl font-extrabold font-mono-tabular text-emerald-400 mt-1">
                              +{newRecs.toLocaleString()}
                            </div>
                          </div>

                          <div className="bg-slate-900/95 border border-slate-700/90 rounded-lg px-3.5 py-2.5">
                            <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                              {lang === 'fa' ? 'کل آرشیو ویکی‌ایران' : 'WikIran Archived'}
                            </div>
                            <div className="text-xl font-extrabold font-mono-tabular text-amber-300 mt-1">
                              {(
                                (liveCrawlStatus?.articles_count ?? data.stats.articles_count) +
                                (liveCrawlStatus?.publications_count ??
                                  data.stats.publications_count) +
                                (data.wikiran_docs_summary?.total ?? 0)
                              ).toLocaleString()}
                            </div>
                          </div>
                        </div>

                        {/* Live URL Stream Ticker when Running */}
                        {isRunningJob && (
                          <div className="bg-slate-900/90 border border-slate-700/80 rounded-lg px-3.5 py-2.5 space-y-1 max-h-32 overflow-y-auto font-mono-tabular text-[11px]">
                            <div className="text-emerald-300 flex items-center gap-2 font-semibold">
                              <RefreshCw className="w-3.5 h-3.5 animate-spin shrink-0" />
                              <span className="truncate">
                                {pipelineLog ||
                                  (lang === 'fa'
                                    ? 'خزنده در حال پیمایش مسیرهای جدید، صفحات لیک‌ها و استخراج لینک‌های داخلی است...'
                                    : 'Spider advancing pagination cursors across /search, /leaks/<slug>?page=K & nested links...')}
                              </span>
                            </div>
                            {(liveCrawlStatus?.recent_history || []).slice(0, 4).map((item) => (
                              <div
                                key={item.id}
                                className="flex items-center justify-between gap-2 text-slate-300 border-t border-slate-800 pt-1"
                              >
                                <span className="truncate">
                                  <span
                                    className={`font-bold me-1.5 ${
                                      item.action_taken === 'INSERTED'
                                        ? 'text-emerald-400'
                                        : item.action_taken === 'UPDATED'
                                        ? 'text-sky-400'
                                        : 'text-slate-400'
                                    }`}
                                  >
                                    [{item.action_taken}]
                                  </span>
                                  {item.target_url.replace('https://wikiran.org', '')}
                                </span>
                                <span className="text-slate-400 shrink-0">{item.record_type}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })()}

                {/* 4 Color-Distinguished Operational Steps */}
                <div className="p-4 sm:p-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                  {/* Step 1: Sky Blue — Lookup Server Updates (Summary Card linked to 4-Mode Spider) */}
                  <div
                    className={`rounded-xl p-4 border-2 border-t-4 border-t-sky-600 transition-all flex flex-col justify-between space-y-4 shadow-xs ${
                      isCrawlingNow
                        ? 'bg-sky-50 border-sky-400 ring-2 ring-sky-200/70'
                        : activePipelineStep === 1
                        ? 'bg-sky-100/70 border-sky-400'
                        : 'bg-gradient-to-b from-sky-50/90 to-white border-sky-200'
                    }`}
                  >
                    <div className="space-y-2.5">
                      <div className="flex items-center justify-between gap-2 text-sky-950">
                        <span className="text-sm font-bold leading-snug">{t.step1Title}</span>
                        {isCrawlingNow ? (
                          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300 shrink-0">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-600 animate-ping" />
                            {lang === 'fa' ? 'زنده' : 'LIVE'}
                          </span>
                        ) : (
                          <span className="p-1.5 rounded-lg bg-sky-100 text-sky-700 shrink-0">
                            <Globe className="w-4 h-4" />
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-slate-600 leading-relaxed">{t.step1Desc}</p>
                    </div>

                    <div className="grid grid-cols-2 gap-1.5">
                      <button
                        type="button"
                        onClick={() => handleUpdateArchive(undefined, 25, true, 'discover')}
                        disabled={isCrawlingNow}
                        className="py-2 px-2 text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700 rounded-md transition-colors cursor-pointer disabled:opacity-50"
                      >
                        {lang === 'fa' ? 'کشف مسیر' : 'Discover'}
                      </button>
                      <button
                        type="button"
                        onClick={() => handleUpdateArchive(undefined, 120, true, 'deep_spider')}
                        disabled={isCrawlingNow}
                        className="py-2 px-2 text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-700 rounded-md transition-colors cursor-pointer disabled:opacity-50"
                      >
                        {lang === 'fa' ? 'خزش عمیق' : 'Deep Spider'}
                      </button>
                      <button
                        type="button"
                        onClick={() => handleUpdateArchive(undefined, 25, false, 'check_updates')}
                        disabled={isCrawlingNow}
                        className="py-2 px-2 text-xs font-bold text-white bg-sky-700 hover:bg-sky-800 rounded-md transition-colors cursor-pointer disabled:opacity-50"
                      >
                        {lang === 'fa' ? 'بررسی آپدیت' : 'Check Updates'}
                      </button>
                      <button
                        type="button"
                        onClick={handleStopCrawl}
                        disabled={!isCrawlingNow}
                        className={`py-2 px-2 text-xs font-bold rounded-md transition-colors ${
                          isCrawlingNow
                            ? 'bg-rose-600 text-white hover:bg-rose-700 cursor-pointer'
                            : 'bg-slate-100 text-slate-400 border border-slate-200 cursor-not-allowed'
                        }`}
                      >
                        {lang === 'fa' ? 'توقف' : 'Stop'}
                      </button>
                    </div>
                  </div>

                  {/* Step 2: Teal — Download & Extract Records */}
                  <div
                    className={`rounded-lg p-4 border border-t-4 border-t-teal-600 transition-colors flex flex-col justify-between space-y-4 ${
                      activePipelineStep === 2
                        ? 'bg-teal-100/80 border-teal-500'
                        : 'bg-teal-50/60 border-teal-200'
                    }`}
                  >
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-teal-950">
                        <span className="text-sm font-bold">{t.step2Title}</span>
                        <ShieldCheck className="w-4 h-4 text-teal-700 shrink-0" />
                      </div>
                      <p className="text-xs text-slate-700 leading-relaxed">{t.step2Desc}</p>
                    </div>
                    <button
                      onClick={() => setActiveNav('history')}
                      className="w-full py-2 px-3 text-xs font-semibold text-white bg-teal-700 hover:bg-teal-800 rounded-md transition-colors inline-flex items-center justify-center gap-1.5 cursor-pointer"
                    >
                      <History className="w-3.5 h-3.5" />
                      <span>{t.step2Action}</span>
                    </button>
                  </div>

                  {/* Step 3: Indigo — Universal SQLite & FTS5 Search */}
                  <div
                    className={`rounded-lg p-4 border border-t-4 border-t-indigo-600 transition-colors flex flex-col justify-between space-y-4 ${
                      activePipelineStep === 3
                        ? 'bg-indigo-100/80 border-indigo-500'
                        : 'bg-indigo-50/60 border-indigo-200'
                    }`}
                  >
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-indigo-950">
                        <span className="text-sm font-bold">{t.step3Title}</span>
                        <Search className="w-4 h-4 text-indigo-700 shrink-0" />
                      </div>
                      <p className="text-xs text-slate-700 leading-relaxed">{t.step3Desc}</p>
                    </div>
                    <button
                      onClick={() => setActiveNav('search')}
                      className="w-full py-2 px-3 text-xs font-semibold text-white bg-indigo-700 hover:bg-indigo-800 rounded-md transition-colors inline-flex items-center justify-center gap-1.5 cursor-pointer"
                    >
                      <Search className="w-3.5 h-3.5" />
                      <span>{t.step3Action}</span>
                    </button>
                  </div>

                  {/* Step 4: Emerald — CSV-to-Excel & Backup */}
                  <div
                    className={`rounded-lg p-4 border border-t-4 border-t-emerald-600 transition-colors flex flex-col justify-between space-y-4 ${
                      activePipelineStep === 4
                        ? 'bg-emerald-100/80 border-emerald-500'
                        : 'bg-emerald-50/60 border-emerald-200'
                    }`}
                  >
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-emerald-950">
                        <span className="text-sm font-bold">{t.step4Title}</span>
                        <FileSpreadsheet className="w-4 h-4 text-emerald-700 shrink-0" />
                      </div>
                      <p className="text-xs text-slate-700 leading-relaxed">{t.step4Desc}</p>
                    </div>
                    <button
                      onClick={() => setActiveNav('exports')}
                      className="w-full py-2 px-3 text-xs font-semibold text-white bg-emerald-700 hover:bg-emerald-800 rounded-md transition-colors inline-flex items-center justify-center gap-1.5 cursor-pointer"
                    >
                      <Table className="w-3.5 h-3.5" />
                      <span>{t.step4Action}</span>
                    </button>
                  </div>
                </div>

                {/* WikIran Structured Archives (Front Companies 2,007 + Vessels 561 + Auto-Cached Leak Docs) */}
                {(() => {
                  const wsum = data.wikiran_docs_summary;
                  const fcCount = wsum?.front_companies ?? 0;
                  const vsCount = wsum?.vessels ?? 0;
                  const cachedLeaks = (wsum?.leaked_emails ?? 0) + (wsum?.leaked_files ?? 0);
                  const isSyncingWikIran =
                    busyAction === 'wikiran_sync_both' ||
                    busyAction === 'wikiran_sync_front-companies' ||
                    busyAction === 'wikiran_sync_vessels';
                  return (
                    <div className="px-4 sm:px-6 pb-5 pt-1">
                      <div className="rounded-xl border-2 border-indigo-200 bg-indigo-50/50 p-4 space-y-3">
                        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
                          <div className="space-y-1">
                            <div className="flex flex-wrap items-center gap-2">
                              <span className="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider bg-indigo-700 text-white rounded">
                                WIKIRAN FULL COVERAGE
                              </span>
                              <h3 className="text-sm font-bold text-slate-900">
                                {lang === 'fa'
                                  ? 'آرشیو شرکت‌های پوششی (۲٬۰۰۷) و کشتی‌ها (۵۶۱) + جستجوی زنده ۵۰۰٬۰۰۰+ سند افشاشده'
                                  : 'WikIran Front Companies (2,007) & Vessels (561) Offline + Live Search across 500,000+ Leak Docs'}
                              </h3>
                            </div>
                            <p className="text-xs text-slate-600 leading-relaxed max-w-3xl">
                              {lang === 'fa'
                                ? 'ویکی‌ایران بیش از ۵۰۰٬۰۰۰ ایمیل و فایل خام در ۲۸ مجموعه افشا دارد. تمام ۲٬۰۰۷ شرکت پوششی و ۵۶۱ کشتی به‌صورت کامل آفلاین ذخیره می‌شوند و هر نامی که در بخش Search & Screen جستجو کنید، همزمان در کل سرور زنده ویکی‌ایران نیز جستجو و به‌طور خودکار آفلاین کش می‌شود.'
                                : 'WikIran hosts 500,000+ raw leaked emails and files across 28 leak collections. Download all 2,007 Front Companies & 561 Vessels offline in one click below — and whenever you search a name in Search & Screen while online, the app also queries WikIran’s full live archive and automatically caches every match offline.'}
                            </p>
                          </div>
                          <div className="flex flex-wrap items-center gap-2 shrink-0">
                            <button
                              type="button"
                              disabled={busyAction !== null || isOffline}
                              onClick={() => handleSyncWikIranArchives('both')}
                              className="px-4 py-2 text-xs font-bold text-white bg-indigo-700 hover:bg-indigo-800 rounded-md transition-colors inline-flex items-center gap-1.5 cursor-pointer shadow-xs disabled:opacity-60"
                            >
                              <HardDriveDownload
                                className={`w-3.5 h-3.5 ${isSyncingWikIran ? 'animate-pulse' : ''}`}
                              />
                              <span>
                                {isSyncingWikIran
                                  ? lang === 'fa'
                                    ? 'در حال دانلود شرکت‌های پوششی و کشتی‌ها...'
                                    : 'Syncing Front Companies & Vessels...'
                                  : lang === 'fa'
                                  ? 'دانلود آفلاین شرکت‌های پوششی (۲٬۰۰۷) و کشتی‌ها (۵۶۱)'
                                  : 'Sync Front Companies (2,007) & Vessels (561) Offline'}
                              </span>
                            </button>
                          </div>
                        </div>

                        {wikiranSyncNote && (
                          <div className="px-3 py-2 rounded-md bg-emerald-50 border border-emerald-200 text-xs font-medium text-emerald-950">
                            {wikiranSyncNote}
                          </div>
                        )}

                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                          <div className="bg-white border border-indigo-200/80 rounded-lg px-3 py-2">
                            <div className="text-[11px] text-slate-500 font-medium">
                              {lang === 'fa' ? 'شرکت‌های پوششی (آفلاین)' : 'Front Companies Offline'}
                            </div>
                            <div className="text-lg font-extrabold font-mono-tabular text-indigo-900">
                              {fcCount.toLocaleString()}{' '}
                              <span className="text-[11px] font-normal text-slate-400">/ 2,007</span>
                            </div>
                          </div>
                          <div className="bg-white border border-indigo-200/80 rounded-lg px-3 py-2">
                            <div className="text-[11px] text-slate-500 font-medium">
                              {lang === 'fa' ? 'کشتی‌ها (آفلاین)' : 'Vessels Archive Offline'}
                            </div>
                            <div className="text-lg font-extrabold font-mono-tabular text-sky-900">
                              {vsCount.toLocaleString()}{' '}
                              <span className="text-[11px] font-normal text-slate-400">/ 561</span>
                            </div>
                          </div>
                          <div className="bg-white border border-indigo-200/80 rounded-lg px-3 py-2">
                            <div className="text-[11px] text-slate-500 font-medium">
                              {lang === 'fa' ? 'اسناد و ایمیل‌های کش‌شده' : 'Cached Leak Emails/Files'}
                            </div>
                            <div className="text-lg font-extrabold font-mono-tabular text-emerald-900">
                              {cachedLeaks.toLocaleString()}
                            </div>
                          </div>
                          <div className="bg-white border border-indigo-200/80 rounded-lg px-3 py-2">
                            <div className="text-[11px] text-slate-500 font-medium">
                              {lang === 'fa' ? 'مقالات و کاتالوگ‌ها' : 'Articles & Leak Guides'}
                            </div>
                            <div className="text-lg font-extrabold font-mono-tabular text-slate-900">
                              {(data.stats.articles_count + data.stats.publications_count).toLocaleString()}
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })()}
              </section>

              {/* U.S. TREASURY OFAC SANCTIONS SUPER-DATASET (OFFLINE TRADE SCREENING + AUTO-UPDATE) */}
              {(() => {
                const ofac = data.ofac_summary;
                const totalOfac = ofac?.total_entities ?? 0;
                const sdnCount = ofac?.sdn_count ?? 0;
                const consCount = ofac?.consolidated_count ?? 0;
                const iranCount = ofac?.iran_related_count ?? 0;
                const pubId = ofac?.last_publication_id || '—';
                const pubDate = (ofac?.last_date_published || '').slice(0, 10) || '—';

                return (
                  <section className="bg-white border-2 border-rose-200 rounded-xl p-4 sm:p-6 shadow-2xs space-y-4">
                    <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-rose-100 pb-4">
                      <div className="space-y-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider bg-rose-600 text-white rounded">
                            OFAC SLS API
                          </span>
                          <h2 className="text-base font-bold text-slate-900">
                            {lang === 'fa'
                              ? 'سوپردیتاست آفلاین تحریم‌های اوفک (OFAC SDN + Consolidated) برای استعلام تجاری'
                              : 'U.S. Treasury OFAC Sanctions Super-Dataset (Offline Trade Screening)'}
                          </h2>
                        </div>
                        <p className="text-xs text-slate-600 leading-relaxed max-w-3xl">
                          {lang === 'fa'
                            ? 'متصل به سرویس رسمی وزارت خزانه‌داری آمریکا (sanctionslistservice.ofac.treas.gov). تمامی لیست‌های SDN و Non-SDN Consolidated به‌همراه اسامی مستعار (AKA)، آدرس‌ها و برنامه‌های تحریمی به‌صورت آفلاین در SQLite FTS5 ذخیره شده و همزمان با آرشیو ویکی‌ایران جستجو می‌شوند.'
                            : 'Connected directly to official U.S. Treasury Sanctions List Service (sanctionslistservice.ofac.treas.gov). Downloads and indexes 100% of SDN & Non-SDN Consolidated entities, aliases (AKAs), addresses, vessels, and remarks into local SQLite FTS5 for instant offline trade counterparty screening alongside WikIran.'}
                        </p>
                      </div>

                      <div className="flex flex-wrap items-center gap-2 shrink-0">
                        <button
                          type="button"
                          disabled={busyAction !== null}
                          onClick={() => handleOfacSync({ check_only: true })}
                          className="px-3.5 py-2 text-xs font-bold text-rose-900 bg-rose-50 hover:bg-rose-100 border border-rose-300 rounded-md transition-colors inline-flex items-center gap-1.5 cursor-pointer disabled:opacity-60"
                        >
                          <RefreshCw
                            className={`w-3.5 h-3.5 ${busyAction === 'ofac_check' ? 'animate-spin' : ''}`}
                          />
                          <span>
                            {busyAction === 'ofac_check'
                              ? lang === 'fa'
                                ? 'در حال بررسی...'
                                : 'Checking OFAC...'
                              : lang === 'fa'
                              ? 'بررسی آپدیت جدید اوفک'
                              : 'Check OFAC Updates'}
                          </span>
                        </button>

                        <button
                          type="button"
                          disabled={busyAction !== null}
                          onClick={() => handleOfacSync({ force: true })}
                          className="px-4 py-2 text-xs font-bold text-white bg-rose-700 hover:bg-rose-800 rounded-md transition-colors inline-flex items-center gap-1.5 cursor-pointer shadow-xs disabled:opacity-60"
                        >
                          <HardDriveDownload
                            className={`w-3.5 h-3.5 ${busyAction === 'ofac_sync' ? 'animate-pulse' : ''}`}
                          />
                          <span>
                            {busyAction === 'ofac_sync'
                              ? lang === 'fa'
                                ? 'در حال دانلود کل لیست‌های اوفک...'
                                : 'Downloading Full OFAC Lists...'
                              : lang === 'fa'
                              ? 'دانلود و همگام‌سازی کامل اوفک'
                              : 'Sync Full OFAC Dataset'}
                          </span>
                        </button>
                      </div>
                    </div>

                    {ofacStatusNote && (
                      <div className="px-3.5 py-2.5 rounded-lg bg-rose-50/80 border border-rose-200 text-xs font-medium text-rose-950">
                        {ofacStatusNote}
                      </div>
                    )}

                    <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
                      <div className="bg-slate-50 border border-slate-200 rounded-lg p-3">
                        <div className="text-[11px] text-slate-500 font-medium">
                          {lang === 'fa' ? 'کل رکوردهای آفلاین اوفک' : 'Total Offline OFAC'}
                        </div>
                        <div className="text-xl font-bold font-mono-tabular text-rose-700 mt-1">
                          {totalOfac.toLocaleString()}
                        </div>
                        <div className="text-[10px] text-slate-500 mt-0.5 font-mono-tabular">
                          {lang === 'fa' ? `نسخه رسمی #${pubId}` : `Treasury Pub #${pubId}`}
                        </div>
                      </div>

                      <div className="bg-slate-50 border border-slate-200 rounded-lg p-3">
                        <div className="text-[11px] text-slate-500 font-medium">
                          {lang === 'fa' ? 'لیست اصلی SDN' : 'SDN List Entries'}
                        </div>
                        <div className="text-xl font-bold font-mono-tabular text-slate-900 mt-1">
                          {sdnCount.toLocaleString()}
                        </div>
                        <div className="text-[10px] text-slate-500 mt-0.5">
                          SDN + ALT + ADD + COMMENTS
                        </div>
                      </div>

                      <div className="bg-slate-50 border border-slate-200 rounded-lg p-3">
                        <div className="text-[11px] text-slate-500 font-medium">
                          {lang === 'fa' ? 'لیست تجمیعی Non-SDN' : 'Non-SDN Consolidated'}
                        </div>
                        <div className="text-xl font-bold font-mono-tabular text-slate-900 mt-1">
                          {consCount.toLocaleString()}
                        </div>
                        <div className="text-[10px] text-slate-500 mt-0.5">
                          FSE · SSI · CAPTA · CMIC
                        </div>
                      </div>

                      <div className="bg-rose-50/70 border border-rose-200 rounded-lg p-3">
                        <div className="text-[11px] text-rose-800 font-semibold">
                          {lang === 'fa' ? 'مرتبط با ایران (IRAN/IRGC)' : 'Iran-Linked Designations'}
                        </div>
                        <div className="text-xl font-bold font-mono-tabular text-rose-800 mt-1">
                          {iranCount.toLocaleString()}
                        </div>
                        <div className="text-[10px] text-rose-700 mt-0.5">
                          IRAN · IRGC · IFSR · EO13902
                        </div>
                      </div>

                      <div className="bg-slate-50 border border-slate-200 rounded-lg p-3">
                        <div className="text-[11px] text-slate-500 font-medium">
                          {lang === 'fa' ? 'آخرین تاریخ انتشار خزانه‌داری' : 'Last Treasury Publish'}
                        </div>
                        <div className="text-base font-bold font-mono-tabular text-slate-900 mt-1">
                          {pubDate}
                        </div>
                        <div className="text-[10px] text-emerald-700 font-semibold mt-0.5">
                          {lang === 'fa'
                            ? 'بررسی خودکار در زمان‌بندی فعال است'
                            : 'Auto-checked in Scheduler'}
                        </div>
                      </div>
                    </div>

                    {ofac && ofac.top_programs && ofac.top_programs.length > 0 && (
                      <div className="flex flex-wrap items-center gap-1.5 pt-1">
                        <span className="text-[11px] font-bold text-slate-600 me-1">
                          {lang === 'fa'
                            ? 'برنامه‌های تحریمی برتر (کلیک برای استعلام):'
                            : 'Top Sanctions Programs (click to screen):'}
                        </span>
                        {ofac.top_programs.slice(0, 8).map((p) => (
                          <button
                            key={p.program}
                            type="button"
                            onClick={() => {
                              setActiveNav('search');
                              setSearchQuery(p.program);
                              setFilterType('OFAC_SANCTION');
                              setSearchScopeTab('ALL');
                              runUniversalSearchWithQuery(p.program, { type: 'OFAC_SANCTION' });
                            }}
                            className="px-2 py-0.5 text-[11px] font-mono-tabular font-semibold bg-rose-50 hover:bg-rose-100 text-rose-900 border border-rose-200 rounded cursor-pointer transition-colors"
                          >
                            {p.program} ({p.count.toLocaleString()})
                          </button>
                        ))}
                      </div>
                    )}
                  </section>
                );
              })()}

              {/* OPENSANCTIONS GLOBAL SANCTIONS SUPER-DATASET (OFFLINE BULK + INDEX.JSON UPDATE CHECKER) */}
              {(() => {
                const os = data.opensanctions_summary;
                const totalOs = os?.total_entities ?? 0;
                const iranOs = os?.iran_related_count ?? 0;
                const catalogCount = os?.catalog_datasets_count ?? 507;
                const lastChange = os?.last_change ? os.last_change.slice(0, 10) : 'Not synced yet';
                return (
                  <section className="bg-white border-2 border-amber-300 rounded-xl p-5 sm:p-6 shadow-xs space-y-4">
                    <div className="flex flex-wrap items-start justify-between gap-4">
                      <div className="space-y-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="px-2.5 py-0.5 text-[11px] font-bold uppercase tracking-wider rounded bg-amber-100 text-amber-950 border border-amber-300">
                            OpenSanctions Global Consolidated
                          </span>
                          <span className="text-xs font-mono-tabular text-slate-500">
                            data.opensanctions.org · UN + EU + UK + US + CH + CA + AU
                          </span>
                        </div>
                        <h2 className="text-base sm:text-lg font-bold text-slate-900">
                          {lang === 'fa'
                            ? 'دیتاست جهانی تحریم‌های OpenSanctions (آفلاین + بررسی خودکار آپدیت)'
                            : 'OpenSanctions Consolidated Global Sanctions (Offline + Auto-Update Check)'}
                        </h2>
                        <p className="text-xs text-slate-600 max-w-3xl">
                          {lang === 'fa'
                            ? 'تمامی لیست‌های تحریمی جهان (سازمان ملل، اتحادیه اروپا، انگلستان، آمریکا، سوئیس، کانادا و استرالیا) را یک‌بار دانلود و استخراج می‌کند تا به‌صورت آفلاین همراه با OFAC و ویکی‌ایران جستجو شوند.'
                            : 'Downloads & extracts OpenSanctions consolidated global sanctions (UN, EU FSF, UK OFSI, US OFAC, Switzerland SECO, Canada, Australia, etc.) offline into SQLite FTS5 with one-click index.json update detection.'}
                        </p>
                      </div>

                      <div className="flex flex-wrap items-center gap-2 shrink-0">
                        <button
                          type="button"
                          onClick={() => handleOpenSanctionsSync({ check_only: true })}
                          disabled={busyAction !== null}
                          className="px-3.5 py-2 text-xs font-semibold text-amber-950 bg-amber-50 hover:bg-amber-100 border border-amber-300 rounded-lg transition-colors inline-flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
                        >
                          <RefreshCw
                            className={`w-3.5 h-3.5 ${busyAction === 'os_check' ? 'animate-spin' : ''}`}
                          />
                          <span>
                            {lang === 'fa' ? 'بررسی آپدیت (index.json)' : 'Check index.json Updates'}
                          </span>
                        </button>
                        <button
                          type="button"
                          onClick={() => handleOpenSanctionsSync({ force: totalOs === 0 })}
                          disabled={busyAction !== null}
                          className="px-4 py-2 text-xs font-bold text-white bg-amber-600 hover:bg-amber-700 rounded-lg transition-colors inline-flex items-center gap-1.5 cursor-pointer disabled:opacity-50 shadow-xs"
                        >
                          <Download className="w-3.5 h-3.5" />
                          <span>
                            {busyAction === 'os_sync'
                              ? lang === 'fa'
                                ? 'در حال دانلود و استخراج OpenSanctions...'
                                : 'Downloading & Extracting OpenSanctions...'
                              : totalOs > 0
                              ? lang === 'fa'
                                ? 'به‌روزرسانی آفلاین OpenSanctions'
                                : 'Sync OpenSanctions Updates'
                              : lang === 'fa'
                              ? 'دانلود و استخراج کامل OpenSanctions (آفلاین)'
                              : 'Download & Extract Global Sanctions (Offline)'}
                          </span>
                        </button>
                      </div>
                    </div>

                    {osStatusNote && (
                      <div className="px-3.5 py-2 rounded-lg bg-amber-50 border border-amber-300 text-xs font-medium text-amber-950 flex items-center justify-between gap-2">
                        <span>{osStatusNote}</span>
                        <button
                          type="button"
                          onClick={() => setOsStatusNote(null)}
                          className="text-amber-800 hover:text-amber-950 cursor-pointer"
                        >
                          <X className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    )}

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                      <div className="bg-slate-50 border border-slate-200 rounded-lg p-3">
                        <div className="text-[11px] text-slate-500 font-medium">
                          {lang === 'fa' ? 'کل اهداف تحریمی آفلاین' : 'Global Offline Targets'}
                        </div>
                        <div className="text-xl font-bold font-mono-tabular text-amber-700 mt-1">
                          {totalOs.toLocaleString()}
                        </div>
                        <div className="text-[10px] text-slate-500 mt-0.5">
                          Consolidated Sanctions CSV
                        </div>
                      </div>
                      <div className="bg-amber-50/70 border border-amber-200 rounded-lg p-3">
                        <div className="text-[11px] text-amber-900 font-semibold">
                          {lang === 'fa' ? 'مرتبط با ایران (IR / IRAN)' : 'Iran-Linked Global Targets'}
                        </div>
                        <div className="text-xl font-bold font-mono-tabular text-amber-800 mt-1">
                          {iranOs.toLocaleString()}
                        </div>
                        <div className="text-[10px] text-amber-700 mt-0.5">
                          EU + UK + UN + US + CA + AU
                        </div>
                      </div>
                      <div className="bg-slate-50 border border-slate-200 rounded-lg p-3">
                        <div className="text-[11px] text-slate-500 font-medium">
                          {lang === 'fa' ? 'دیتاست‌های رسمی کاتالوگ' : 'Catalog Datasets Indexed'}
                        </div>
                        <div className="text-xl font-bold font-mono-tabular text-slate-900 mt-1">
                          {catalogCount.toLocaleString()}
                        </div>
                        <div className="text-[10px] text-slate-500 mt-0.5">
                          index.json live registry
                        </div>
                      </div>
                      <div className="bg-slate-50 border border-slate-200 rounded-lg p-3">
                        <div className="text-[11px] text-slate-500 font-medium">
                          {lang === 'fa' ? 'آخرین تغییر OpenSanctions' : 'Last Dataset Change'}
                        </div>
                        <div className="text-base font-bold font-mono-tabular text-slate-900 mt-1">
                          {lastChange}
                        </div>
                        <div className="text-[10px] text-emerald-700 font-semibold mt-0.5">
                          {totalOs > 0
                            ? lang === 'fa'
                              ? 'آماده جستجوی آفلاین'
                              : 'Offline FTS5 Ready'
                            : lang === 'fa'
                            ? 'روی دانلود کلیک کنید'
                            : 'Click Download to sync'}
                        </div>
                      </div>
                    </div>

                    {os && os.top_source_lists && os.top_source_lists.length > 0 && (
                      <div className="flex flex-wrap items-center gap-1.5 pt-1">
                        <span className="text-[11px] font-bold text-slate-600 me-1">
                          {lang === 'fa'
                            ? 'منابع تحریمی برتر (کلیک برای استعلام):'
                            : 'Top Global Source Lists (click to screen):'}
                        </span>
                        {os.top_source_lists.slice(0, 8).map((src) => (
                          <button
                            key={src.list}
                            type="button"
                            onClick={() => {
                              setActiveNav('search');
                              setSearchQuery(src.list);
                              setFilterType('OPENSANCTIONS');
                              setSearchScopeTab('ALL');
                              runUniversalSearchWithQuery(src.list, { type: 'OPENSANCTIONS' });
                            }}
                            className="px-2 py-0.5 text-[11px] font-mono-tabular font-semibold bg-amber-50 hover:bg-amber-100 text-amber-950 border border-amber-200 rounded cursor-pointer transition-colors"
                          >
                            {src.list} ({src.count.toLocaleString()})
                          </button>
                        ))}
                      </div>
                    )}
                  </section>
                );
              })()}

              {/* QUICK ACTIONS */}
              <section className="space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h2 className="text-base font-bold text-slate-900">{t.quickActionsTitle}</h2>
                  {(busyAction === 'update' || busyAction === 'pipeline') && (
                    <button
                      type="button"
                      onClick={handleStopCrawl}
                      className="px-3 py-1.5 text-xs font-bold text-white bg-red-600 hover:bg-red-700 rounded-md inline-flex items-center gap-1.5 cursor-pointer shadow-xs"
                    >
                      <Square className="w-3 h-3 fill-current" />
                      <span>{lang === 'fa' ? 'توقف خزش (Stop)' : 'Stop Active Spider Crawl'}</span>
                    </button>
                  )}
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
                  {/* Core Action 1: Search & Screen Counterparties (OFAC + WikIran) */}
                  <button
                    onClick={() => setActiveNav('search')}
                    className="flex flex-col justify-between p-4 bg-white border border-indigo-200 border-t-4 border-t-indigo-600 rounded-lg hover:bg-indigo-50/50 transition-colors text-start cursor-pointer space-y-3 shadow-2xs"
                  >
                    <div className="flex items-center justify-between w-full">
                      <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-indigo-100 text-indigo-900">
                        OFAC + WikIran
                      </span>
                      <Search className="w-4 h-4 text-indigo-700 shrink-0" />
                    </div>
                    <div>
                      <div className="text-sm font-bold text-slate-900">
                        {lang === 'fa' ? 'جستجو و استعلام تجاری' : 'Search & Screen Names'}
                      </div>
                      <div className="text-xs text-slate-600 mt-0.5">
                        {lang === 'fa'
                          ? 'بررسی آفلاین ۲۰٬۰۸۵ رکورد اوفک + کل ویکی‌ایران'
                          : 'Offline check across 20,085 OFAC + WikIran'}
                      </div>
                    </div>
                  </button>

                  {/* Core Action 2: Export Excel & Human-Readable Converter */}
                  <button
                    onClick={() => setActiveNav('exports')}
                    className="flex flex-col justify-between p-4 bg-white border border-emerald-200 border-t-4 border-t-emerald-600 rounded-lg hover:bg-emerald-50/50 transition-colors text-start cursor-pointer space-y-3 shadow-2xs"
                  >
                    <div className="flex items-center justify-between w-full">
                      <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-emerald-100 text-emerald-900">
                        Excel (.xlsx)
                      </span>
                      <FileSpreadsheet className="w-4 h-4 text-emerald-700 shrink-0" />
                    </div>
                    <div>
                      <div className="text-sm font-bold text-slate-900">
                        {lang === 'fa' ? 'خروجی اکسل و مبدل خوانا' : 'Export & Data Converter'}
                      </div>
                      <div className="text-xs text-slate-600 mt-0.5">
                        {lang === 'fa'
                          ? 'ساخت گزارش اوفک/ویکی‌ایران و تبدیل خوانای CSV'
                          : 'OFAC & WikIran Excel reports + Human CSV viewer'}
                      </div>
                    </div>
                  </button>

                  {/* Core Action 3: Sync OFAC Sanctions */}
                  <button
                    onClick={() => handleOfacSync({ force: false })}
                    disabled={busyAction !== null}
                    className="flex flex-col justify-between p-4 bg-white border border-rose-200 border-t-4 border-t-rose-600 rounded-lg hover:bg-rose-50/50 transition-colors text-start disabled:opacity-50 cursor-pointer space-y-3 shadow-2xs"
                  >
                    <div className="flex items-center justify-between w-full">
                      <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-rose-100 text-rose-900">
                        U.S. Treasury
                      </span>
                      <RefreshCw
                        className={`w-4 h-4 text-rose-700 shrink-0 ${
                          busyAction === 'ofac_sync' || busyAction === 'ofac_check'
                            ? 'animate-spin'
                            : ''
                        }`}
                      />
                    </div>
                    <div>
                      <div className="text-sm font-bold text-slate-900">
                        {lang === 'fa' ? 'به‌روزرسانی لیست‌های اوفک' : 'Check & Sync OFAC'}
                      </div>
                      <div className="text-xs text-slate-600 mt-0.5">
                        {lang === 'fa'
                          ? 'بررسی آخرین نسخه SDN و Consolidated خزانه‌داری'
                          : 'Check latest SDN & Consolidated delta updates'}
                      </div>
                    </div>
                  </button>

                  {/* Core Action 4: Create SQLite Backup */}
                  <button
                    onClick={handleCreateBackup}
                    disabled={busyAction === 'backup'}
                    className="flex flex-col justify-between p-4 bg-white border border-purple-300 border-t-4 border-t-purple-600 rounded-lg hover:bg-purple-50/50 transition-colors text-start disabled:opacity-50 cursor-pointer space-y-3 shadow-2xs"
                  >
                    <div className="flex items-center justify-between w-full">
                      <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-purple-100 text-purple-950">
                        {t.adminBadge}
                      </span>
                      <HardDriveDownload className="w-4 h-4 text-purple-700 shrink-0" />
                    </div>
                    <div>
                      <div className="text-sm font-bold text-slate-900">{t.actionCreateBackup}</div>
                      <div className="text-xs text-slate-600 mt-0.5">
                        Verified SQLite Snapshot ({data.backups.length} saved)
                      </div>
                    </div>
                  </button>

                  {/* Admin Task 3: Scheduled Auto-Sync */}
                  <button
                    onClick={() => setActiveNav('settings')}
                    className="flex flex-col justify-between p-4 bg-white border border-cyan-300 border-t-4 border-t-cyan-600 rounded-lg hover:bg-cyan-50/50 transition-colors text-start cursor-pointer space-y-3 shadow-2xs"
                  >
                    <div className="flex items-center justify-between w-full">
                      <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-cyan-100 text-cyan-950">
                        {t.adminBadge}
                      </span>
                      <Clock className="w-4 h-4 text-cyan-700 shrink-0" />
                    </div>
                    <div>
                      <div className="text-sm font-bold text-slate-900">
                        {lang === 'fa' ? 'زمان‌بندی خودکار دریافت' : 'Scheduled Auto-Sync'}
                      </div>
                      <div className="text-xs text-slate-600 mt-0.5 font-mono-tabular">
                        {data.schedule?.frequency} @ {data.schedule?.time_utc} UTC
                      </div>
                    </div>
                  </button>

                  {/* Clerk / All Task 4: Open Visual Workflow Modal */}
                  <button
                    onClick={() => setShowWorkflowModal(true)}
                    className="flex flex-col justify-between p-4 bg-white border border-rose-200 border-t-4 border-t-rose-600 rounded-lg hover:bg-rose-50/50 transition-colors text-start cursor-pointer space-y-3 shadow-2xs"
                  >
                    <div className="flex items-center justify-between w-full">
                      <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-rose-100 text-rose-900">
                        {t.clerkBadge}
                      </span>
                      <HelpCircle className="w-4 h-4 text-rose-700 shrink-0" />
                    </div>
                    <div>
                      <div className="text-sm font-bold text-slate-900">{t.actionHelp}</div>
                      <div className="text-xs text-slate-600 mt-0.5">
                        Step-by-Step Visual Walkthrough
                      </div>
                    </div>
                  </button>
                </div>
              </section>

              {/* Color-Distinguished KPI Metrics Strip */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="bg-white border border-blue-200 border-t-4 border-t-blue-600 rounded-lg p-5">
                  <div className="text-xs font-semibold text-blue-800">{t.statArticles}</div>
                  <div className="text-2xl font-bold text-slate-900 font-mono-tabular mt-1">
                    {data.stats.articles_count}
                  </div>
                  <div className="text-xs text-slate-500 mt-1">
                    /document/articles/* · Verified
                  </div>
                </div>
                <div className="bg-white border border-teal-200 border-t-4 border-t-teal-600 rounded-lg p-5">
                  <div className="text-xs font-semibold text-teal-800">{t.statPublications}</div>
                  <div className="text-2xl font-bold text-slate-900 font-mono-tabular mt-1">
                    {data.stats.publications_count}
                  </div>
                  <div className="text-xs text-slate-500 mt-1">
                    /leaks & /archives · Indexed
                  </div>
                </div>
                <div className="bg-white border border-amber-200 border-t-4 border-t-amber-600 rounded-lg p-5">
                  <div className="text-xs font-semibold text-amber-800">{t.statOrganizations}</div>
                  <div className="text-2xl font-bold text-slate-900 font-mono-tabular mt-1">
                    {data.stats.organizations_count}
                  </div>
                  <div className="text-xs text-slate-500 mt-1">
                    {data.stats.entities_count} Entities Linked
                  </div>
                </div>
                <div className="bg-white border border-emerald-200 border-t-4 border-t-emerald-600 rounded-lg p-5">
                  <div className="text-xs font-semibold text-emerald-800">
                    {lang === 'fa'
                      ? 'فایل‌های CSV و دفاتر اسناد/ایمیل‌ها'
                      : 'Indexed CSV & Ledger Spreadsheets'}
                  </div>
                  <div className="text-2xl font-bold text-slate-900 font-mono-tabular mt-1">
                    {data.csv_datasets?.length || 2}
                  </div>
                  <div className="text-xs text-slate-500 mt-1">
                    {(data.csv_datasets || []).reduce((acc, d) => acc + d.row_count, 0)} Rows Searchable
                  </div>
                </div>
              </div>

              {/* RECHARTS VISUALIZATION SECTION: Collection Trends & Database Growth */}
              <section className="bg-white border border-slate-200 rounded-xl p-4 sm:p-6 space-y-5">
                <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-100 pb-4">
                  <div>
                    <h2 className="text-base font-bold text-slate-900">{t.chartsTitle}</h2>
                    <p className="text-xs text-slate-500">{t.chartsSubtitle}</p>
                  </div>
                  <div className="text-xs font-mono-tabular text-indigo-700 bg-indigo-50 px-3 py-1.5 rounded-md border border-indigo-200">
                    Scheduled Auto-Update: {data.schedule?.frequency?.toUpperCase()} @{' '}
                    {data.schedule?.time_utc} UTC
                  </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* Chart 1: BarChart of Articles & Catalogues Collected per Period */}
                  <div className="border border-slate-200 rounded-lg p-4 bg-slate-50/50">
                    <div className="text-xs font-semibold text-slate-700 mb-3">
                      {t.chartArticlesLabel}
                    </div>
                    <div className="h-64 w-full" dir="ltr">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={data.trends || []}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                          <XAxis dataKey="period" tick={{ fontSize: 11, fill: '#475569' }} />
                          <YAxis tick={{ fontSize: 11, fill: '#475569' }} />
                          <Tooltip
                            contentStyle={{
                              backgroundColor: '#FFFFFF',
                              borderColor: '#CBD5E1',
                              fontSize: '12px',
                              borderRadius: '6px',
                            }}
                          />
                          <Legend wrapperStyle={{ fontSize: '12px' }} />
                          <Bar
                            dataKey="articles_collected"
                            name={lang === 'fa' ? 'مقالات' : 'Articles'}
                            fill="#2563EB"
                            radius={[4, 4, 0, 0]}
                          />
                          <Bar
                            dataKey="catalogues_collected"
                            name={lang === 'fa' ? 'فهرست انتشارات' : 'Catalogues'}
                            fill="#0D9488"
                            radius={[4, 4, 0, 0]}
                          />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  {/* Chart 2: AreaChart of Cumulative Database Growth */}
                  <div className="border border-slate-200 rounded-lg p-4 bg-slate-50/50">
                    <div className="text-xs font-semibold text-slate-700 mb-3">
                      {t.chartGrowthLabel}
                    </div>
                    <div className="h-64 w-full" dir="ltr">
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={data.trends || []}>
                          <defs>
                            <linearGradient id="growthGradient" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor="#4F46E5" stopOpacity={0.35} />
                              <stop offset="95%" stopColor="#4F46E5" stopOpacity={0.02} />
                            </linearGradient>
                          </defs>
                          <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                          <XAxis dataKey="period" tick={{ fontSize: 11, fill: '#475569' }} />
                          <YAxis tick={{ fontSize: 11, fill: '#475569' }} />
                          <Tooltip
                            contentStyle={{
                              backgroundColor: '#FFFFFF',
                              borderColor: '#CBD5E1',
                              fontSize: '12px',
                              borderRadius: '6px',
                            }}
                          />
                          <Legend wrapperStyle={{ fontSize: '12px' }} />
                          <Area
                            type="monotone"
                            dataKey="total_database_growth"
                            name={lang === 'fa' ? 'کل رکوردهای آرشیو' : 'Total Archive Records'}
                            stroke="#4F46E5"
                            strokeWidth={2.5}
                            fillOpacity={1}
                            fill="url(#growthGradient)"
                          />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                </div>
              </section>
            </div>
          )}

          {activeNav === 'watchlist' && (
            <BatchWatchlistPanel lang={lang} onDataUpdated={fetchOverview} />
          )}

          {activeNav === 'targeted_leaks' && (
            <TargetedLeakDownloaderPanel lang={lang} onDataUpdated={fetchOverview} />
          )}

          {/* 2. UNIVERSAL SEARCH ARCHIVE (Checks ALL Downloaded Data: Articles, Publications, Emails, Files, Banking IBANs, CSV Rows, Entities) */}
          {activeNav === 'search' && (
            <div className="space-y-6">
              <form
                onSubmit={handleSearch}
                className="bg-white border-2 border-indigo-200 rounded-xl p-4 sm:p-6 space-y-4 shadow-2xs"
              >
                <div className="flex flex-col md:flex-row gap-3">
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder={t.searchPlaceholder}
                    className="flex-1 px-3.5 py-2.5 text-sm border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-600"
                  />
                  <button
                    type="submit"
                    disabled={busyAction === 'search'}
                    className="px-5 py-2.5 text-sm font-semibold text-white bg-indigo-600 rounded-md hover:bg-indigo-700 transition-colors whitespace-nowrap cursor-pointer"
                  >
                    {t.btnSearch}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setSearchQuery('');
                      setFilterCategory('ALL');
                      setFilterOrg('ALL');
                      setFilterType('ALL');
                      setFilterDateFrom('');
                      setFilterDateTo('');
                      setActiveLeakSourceFilter('');
                      setWikiranLiveMeta(null);
                      setSearchResults(null);
                    }}
                    className="px-4 py-2.5 text-sm font-medium text-slate-700 bg-slate-100 rounded-md hover:bg-slate-200 transition-colors whitespace-nowrap cursor-pointer"
                  >
                    {t.btnReset}
                  </button>
                </div>

                {/* Live Full-Archive WikIran Server Toggle (searches all 500,000+ emails, files, Front Companies & Vessels) */}
                <div className="flex flex-wrap items-center justify-between gap-2 px-3 py-2 rounded-lg bg-indigo-50/70 border border-indigo-200 text-xs">
                  <label className="inline-flex items-center gap-2 font-semibold text-indigo-950 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={includeLiveWikIran && !isOffline}
                      disabled={isOffline}
                      onChange={(e) => {
                        const next = e.target.checked;
                        setIncludeLiveWikIran(next);
                        if (searchQuery.trim()) {
                          runUniversalSearchWithQuery(searchQuery, { includeLive: next });
                        }
                      }}
                      className="w-4 h-4 accent-indigo-700 rounded cursor-pointer"
                    />
                    <span>
                      {lang === 'fa'
                        ? 'جستجوی همزمان در کل آرشیو زنده WikIran.org (بیش از ۵۰۰٬۰۰۰ ایمیل، سند، شرکت پوششی و کشتی + ذخیره خودکار آفلاین)'
                        : 'Also query Live WikIran.org Full Archive (500,000+ leaked emails, PDFs, Front Companies & Vessels — auto-saves hits offline)'}
                    </span>
                  </label>
                  <span
                    className={`px-2 py-0.5 rounded font-bold text-[10px] uppercase ${
                      isOffline
                        ? 'bg-slate-200 text-slate-600'
                        : includeLiveWikIran
                        ? 'bg-emerald-600 text-white'
                        : 'bg-slate-200 text-slate-700'
                    }`}
                  >
                    {isOffline
                      ? 'Offline (Local Only)'
                      : includeLiveWikIran
                      ? 'Live + Offline Active'
                      : 'Offline Only'}
                  </span>
                </div>

                {/* Instant Sample Deep-Search Chips (Emails, Banking IBANs, Files, Companies) */}
                <div className="flex flex-wrap items-center gap-2 pt-1">
                  <span className="text-xs font-semibold text-slate-500">
                    {lang === 'fa'
                      ? 'نمونه جستجو در کل داده‌های دانلودشده:'
                      : 'Try searching across all downloaded data:'}
                  </span>
                  {[
                    { label: 'Sahara Thunder (OFAC + WikIran)', query: 'Sahara Thunder' },
                    { label: 'Bank Melli (OFAC + WikIran)', query: 'Bank Melli' },
                    { label: 'IRISL (Shipping Sanctions)', query: 'IRISL' },
                    { label: 'Mahan Air (OFAC)', query: 'Mahan Air' },
                    { label: 'settlements@rahbar (Email)', query: 'settlements@rahbar' },
                    { label: 'MODAFL', query: 'MODAFL' },
                  ].map((chip) => (
                    <button
                      key={chip.query}
                      type="button"
                      onClick={() => {
                        setSearchQuery(chip.query);
                        setFilterType('ALL');
                        setSearchScopeTab('ALL');
                        runUniversalSearchWithQuery(chip.query, { type: 'ALL' });
                      }}
                      className="px-2.5 py-1 text-xs font-mono-tabular bg-indigo-50 text-indigo-800 border border-indigo-200 rounded hover:bg-indigo-100 transition-colors cursor-pointer"
                    >
                      {chip.label}
                    </button>
                  ))}
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
                  <select
                    value={filterCategory}
                    onChange={(e) => {
                      const nextVal = e.target.value;
                      setFilterCategory(nextVal);
                      runUniversalSearchWithQuery(searchQuery, { category: nextVal });
                    }}
                    className="px-3 py-2 text-xs border border-slate-300 rounded-md bg-white"
                  >
                    <option value="ALL">{t.filterCategory}</option>
                    {data.categories.map((c) => (
                      <option key={c.slug} value={c.slug}>
                        {isRtl ? c.name_fa : c.name_en}
                      </option>
                    ))}
                  </select>

                  <select
                    value={filterOrg}
                    onChange={(e) => {
                      const nextVal = e.target.value;
                      setFilterOrg(nextVal);
                      runUniversalSearchWithQuery(searchQuery, { org: nextVal });
                    }}
                    className="px-3 py-2 text-xs border border-slate-300 rounded-md bg-white"
                  >
                    <option value="ALL">{t.filterOrganization}</option>
                    {data.organizations.map((o) => (
                      <option key={o.id} value={o.acronym || o.name}>
                        {o.name}
                      </option>
                    ))}
                  </select>

                  <select
                    value={filterType}
                    onChange={(e) => {
                      const nextVal = e.target.value;
                      setFilterType(nextVal);
                      setSearchScopeTab('ALL');
                      runUniversalSearchWithQuery(searchQuery, { type: nextVal });
                    }}
                    className="px-3 py-2 text-xs border border-slate-300 rounded-md bg-white font-semibold text-indigo-950"
                  >
                    <option value="ALL">{t.filterSourceType}</option>
                    <option value="OFAC_SANCTION">
                      OFAC Sanctions Lists (SDN + Non-SDN Consolidated)
                    </option>
                    <option value="OPENSANCTIONS">
                      OpenSanctions Global Consolidated (UN, EU, UK, US, CA, AU, CH)
                    </option>
                    <option value="WIKIRAN_DOC">
                      WikIran Front Companies, Vessels & Cached Leak Docs
                    </option>
                    <option value="ARTICLE">Articles (/document/articles/*)</option>
                    <option value="PUBLICATION">Publication Catalogues (/leak/*)</option>
                    <option value="CSV_ROW">
                      CSV / Excel Rows (Emails, Banking Ledgers & Tables)
                    </option>
                    <option value="FILE_INVENTORY">File & Document Inventory</option>
                    <option value="ENTITY">Organizations & Entities</option>
                  </select>
                </div>

                {/* Publication Date Range Filter (Matching Export Report Wizard) */}
                {(() => {
                  const matchedArticlesCount = displayedSearchResults.filter(
                    (r) => r.record_type === 'ARTICLE'
                  ).length;
                  const matchedPubsCount = displayedSearchResults.filter(
                    (r) => r.record_type === 'PUBLICATION'
                  ).length;
                  return (
                    <div className="bg-slate-50/80 border border-slate-200 rounded-lg p-3.5 space-y-3">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="flex items-center gap-2 text-xs font-bold text-slate-800">
                          <Calendar className="w-4 h-4 text-indigo-600 shrink-0" />
                          <span>
                            {lang === 'fa'
                              ? 'فیلتر بازه زمانی تاریخ انتشار (مقالات و انتشارات):'
                              : 'Publication Date Range Filter (Articles & Publications):'}
                          </span>
                        </div>
                        <div className="flex flex-wrap items-center gap-1.5">
                          <button
                            type="button"
                            onClick={() => {
                              setFilterDateFrom('2026-01-01');
                              setFilterDateTo('2026-12-31');
                              runUniversalSearchWithQuery(searchQuery, {
                                from: '2026-01-01',
                                to: '2026-12-31',
                              });
                            }}
                            className={`px-2.5 py-1 text-[11px] font-semibold border rounded cursor-pointer transition-colors ${
                              filterDateFrom === '2026-01-01' && filterDateTo === '2026-12-31'
                                ? 'bg-indigo-600 text-white border-indigo-600'
                                : 'bg-white hover:bg-indigo-50 text-slate-700 hover:text-indigo-800 border-slate-300'
                            }`}
                          >
                            2026
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              setFilterDateFrom('2025-01-01');
                              setFilterDateTo('2026-12-31');
                              runUniversalSearchWithQuery(searchQuery, {
                                from: '2025-01-01',
                                to: '2026-12-31',
                              });
                            }}
                            className={`px-2.5 py-1 text-[11px] font-semibold border rounded cursor-pointer transition-colors ${
                              filterDateFrom === '2025-01-01' && filterDateTo === '2026-12-31'
                                ? 'bg-indigo-600 text-white border-indigo-600'
                                : 'bg-white hover:bg-indigo-50 text-slate-700 hover:text-indigo-800 border-slate-300'
                            }`}
                          >
                            2025–2026
                          </button>
                          {(filterDateFrom || filterDateTo) && (
                            <button
                              type="button"
                              onClick={() => {
                                setFilterDateFrom('');
                                setFilterDateTo('');
                                runUniversalSearchWithQuery(searchQuery, {
                                  from: '',
                                  to: '',
                                });
                              }}
                              className="px-2.5 py-1 text-[11px] font-semibold bg-red-50 hover:bg-red-100 text-red-700 border border-red-200 rounded cursor-pointer transition-colors"
                            >
                              {lang === 'fa' ? 'پاک کردن بازه' : 'Clear Dates'}
                            </button>
                          )}
                        </div>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 items-end">
                        <div className="space-y-1">
                          <label className="block text-[11px] font-semibold text-slate-600">
                            {lang === 'fa' ? 'از تاریخ (Start Date):' : 'Start Date (From):'}
                          </label>
                          <input
                            type="date"
                            value={filterDateFrom}
                            onChange={(e) => {
                              const nextFrom = e.target.value;
                              setFilterDateFrom(nextFrom);
                              runUniversalSearchWithQuery(searchQuery, { from: nextFrom });
                            }}
                            aria-label={t.filterDateFrom}
                            className="w-full px-3 py-2 text-xs font-mono-tabular border border-slate-300 rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-indigo-600"
                          />
                        </div>
                        <div className="space-y-1">
                          <label className="block text-[11px] font-semibold text-slate-600">
                            {lang === 'fa' ? 'تا تاریخ (End Date):' : 'End Date (To):'}
                          </label>
                          <input
                            type="date"
                            value={filterDateTo}
                            onChange={(e) => {
                              const nextTo = e.target.value;
                              setFilterDateTo(nextTo);
                              runUniversalSearchWithQuery(searchQuery, { to: nextTo });
                            }}
                            aria-label={t.filterDateTo}
                            className="w-full px-3 py-2 text-xs font-mono-tabular border border-slate-300 rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-indigo-600"
                          />
                        </div>
                        <div className="px-3 py-2 rounded-md bg-indigo-50/80 border border-indigo-200 text-xs text-indigo-950 font-medium">
                          {filterDateFrom || filterDateTo ? (
                            <span>
                              {lang === 'fa'
                                ? `مطابق بازه زمانی: ${matchedArticlesCount} مقاله · ${matchedPubsCount} انتشار`
                                : `Matching Date Range: ${matchedArticlesCount} Articles · ${matchedPubsCount} Publications`}
                            </span>
                          ) : (
                            <span className="text-slate-600">
                              {lang === 'fa'
                                ? 'همه تاریخ‌های انتشار شامل می‌شوند (بدون محدودیت زمانی)'
                                : 'All publication dates included (no date restriction)'}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })()}
              </form>

              {(() => {
                const ofacMatches = displayedSearchResults.filter(
                  (r) => r.record_type === 'OFAC_SANCTION'
                );
                const osMatches = displayedSearchResults.filter(
                  (r) => r.record_type === 'OPENSANCTIONS'
                );
                const wikiranMatches = displayedSearchResults.filter(
                  (r) => r.record_type !== 'OFAC_SANCTION' && r.record_type !== 'OPENSANCTIONS'
                );
                const totalSanctionsHits = ofacMatches.length + osMatches.length;
                const scopedResults =
                  searchScopeTab === 'OFAC'
                    ? ofacMatches
                    : searchScopeTab === 'OPENSANCTIONS'
                    ? osMatches
                    : searchScopeTab === 'WIKIRAN'
                    ? wikiranMatches
                    : displayedSearchResults;

                return (
                  <div className="space-y-3">
                    {/* Trade Counterparty OFAC + OpenSanctions + WikIran Screening Verdict Banner */}
                    {Boolean(searchQuery.trim()) && searchResults !== null && (
                      <div
                        className={`rounded-lg border-2 p-3.5 flex flex-wrap items-center justify-between gap-3 ${
                          totalSanctionsHits > 0
                            ? 'bg-rose-50 border-rose-300 text-rose-950'
                            : 'bg-emerald-50 border-emerald-300 text-emerald-950'
                        }`}
                      >
                        <div className="flex items-center gap-2.5">
                          {totalSanctionsHits > 0 ? (
                            <AlertTriangle className="w-5 h-5 text-rose-600 shrink-0" />
                          ) : (
                            <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
                          )}
                          <div className="space-y-0.5">
                            <div className="text-xs sm:text-sm font-bold">
                              {totalSanctionsHits > 0
                                ? lang === 'fa'
                                  ? `هشدار تحریم تجاری: ${ofacMatches.length} تطابق در اوفک (OFAC) و ${osMatches.length} تطابق در OpenSanctions جهانی یافت شد!`
                                  : `SANCTIONS SCREENING ALERT: ${ofacMatches.length} OFAC + ${osMatches.length} OpenSanctions Match(es) Found!`
                                : lang === 'fa'
                                ? `بدون تطابق تحریمی در ${Number(data.ofac_summary?.total_entities || 0).toLocaleString()} رکورد OFAC و ${Number(data.opensanctions_summary?.total_entities || 0).toLocaleString()} رکورد OpenSanctions`
                                : `Sanctions Clear: 0 Hits across ${Number(data.ofac_summary?.total_entities || 0).toLocaleString()} OFAC & ${Number(data.opensanctions_summary?.total_entities || 0).toLocaleString()} OpenSanctions offline records`}
                            </div>
                            <div className="text-[11px] opacity-85">
                              {lang === 'fa'
                                ? `آرشیو ویکی‌ایران: ${wikiranMatches.length} رکورد · اوفک #${data.ofac_summary?.last_publication_id || '—'} · OpenSanctions ${data.opensanctions_summary?.last_change?.slice(0, 10) || '—'}`
                                : `WikIran Archive: ${wikiranMatches.length} records · OFAC Pub #${data.ofac_summary?.last_publication_id || '—'} · OpenSanctions ${data.opensanctions_summary?.last_change?.slice(0, 10) || '—'}`}
                            </div>
                          </div>
                        </div>

                        <div className="flex flex-wrap items-center gap-1.5">
                          <button
                            type="button"
                            onClick={() => setSearchScopeTab('ALL')}
                            className={`px-2.5 py-1 text-xs font-bold rounded border cursor-pointer transition-colors ${
                              searchScopeTab === 'ALL'
                                ? 'bg-slate-900 text-white border-slate-900'
                                : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-100'
                            }`}
                          >
                            {lang === 'fa' ? 'همه' : 'All'} ({displayedSearchResults.length})
                          </button>
                          <button
                            type="button"
                            onClick={() => setSearchScopeTab('OFAC')}
                            className={`px-2.5 py-1 text-xs font-bold rounded border cursor-pointer transition-colors ${
                              searchScopeTab === 'OFAC'
                                ? 'bg-rose-700 text-white border-rose-700'
                                : 'bg-white text-rose-800 border-rose-300 hover:bg-rose-50'
                            }`}
                          >
                            OFAC ({ofacMatches.length})
                          </button>
                          <button
                            type="button"
                            onClick={() => setSearchScopeTab('OPENSANCTIONS')}
                            className={`px-2.5 py-1 text-xs font-bold rounded border cursor-pointer transition-colors ${
                              searchScopeTab === 'OPENSANCTIONS'
                                ? 'bg-amber-600 text-white border-amber-600'
                                : 'bg-white text-amber-900 border-amber-300 hover:bg-amber-50'
                            }`}
                          >
                            OpenSanctions ({osMatches.length})
                          </button>
                          <button
                            type="button"
                            onClick={() => setSearchScopeTab('WIKIRAN')}
                            className={`px-2.5 py-1 text-xs font-bold rounded border cursor-pointer transition-colors ${
                              searchScopeTab === 'WIKIRAN'
                                ? 'bg-indigo-700 text-white border-indigo-700'
                                : 'bg-white text-indigo-800 border-indigo-300 hover:bg-indigo-50'
                            }`}
                          >
                            WikIran ({wikiranMatches.length})
                          </button>
                        </div>
                      </div>
                    )}

                    {/* Live WikIran Full-Archive Server Results Banner + Clickable Leak Source Facets */}
                    {wikiranLiveMeta && Boolean(searchQuery.trim()) && (
                      <div className="rounded-lg border-2 border-indigo-300 bg-indigo-50/75 p-3.5 space-y-2.5">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider bg-indigo-700 text-white rounded">
                              {wikiranLiveMeta.online ? 'WIKIRAN.ORG LIVE SERVER' : 'WIKIRAN LIVE OFFLINE'}
                            </span>
                            <span className="text-xs sm:text-sm font-bold text-indigo-950">
                              {wikiranLiveMeta.online
                                ? lang === 'fa'
                                  ? `سرور زنده ویکی‌ایران: ${wikiranLiveMeta.total_label} (${wikiranLiveMeta.fetched_count} مورد بارگذاری شد · ${wikiranLiveMeta.cached_new_count} مورد جدید آفلاین ذخیره شد)`
                                  : `WikIran.org Full Archive: ${wikiranLiveMeta.total_label} (${wikiranLiveMeta.fetched_count} top hits loaded · ${wikiranLiveMeta.cached_new_count} newly saved offline)`
                                : lang === 'fa'
                                ? 'سرور زنده ویکی‌ایران در دسترس نیست (نمایش نتایج آفلاین محلی)'
                                : 'Live WikIran server unreachable — showing 100% local offline SQLite matches'}
                            </span>
                          </div>
                          {wikiranLiveMeta.search_url && (
                            <a
                              href={wikiranLiveMeta.search_url}
                              target="_blank"
                              rel="noreferrer"
                              className="px-3 py-1 text-xs font-bold text-indigo-900 bg-white hover:bg-indigo-100 border border-indigo-300 rounded-md inline-flex items-center gap-1.5 transition-colors"
                            >
                              <span>
                                {lang === 'fa' ? 'مشاهده کل نتایج در WikIran.org' : 'Open Full Query on WikIran.org'}
                              </span>
                              <ExternalLink className="w-3.5 h-3.5" />
                            </a>
                          )}
                        </div>

                        {wikiranLiveMeta.online && wikiranLiveMeta.facets && wikiranLiveMeta.facets.length > 0 && (
                          <div className="flex flex-wrap items-center gap-1.5">
                            <span className="text-[11px] font-semibold text-indigo-900 me-1">
                              {lang === 'fa' ? 'تفکیک مجموعه‌های افشا:' : 'Matched Leak Collections:'}
                            </span>
                            {activeLeakSourceFilter && (
                              <button
                                type="button"
                                onClick={() => {
                                  setActiveLeakSourceFilter('');
                                  runUniversalSearchWithQuery(searchQuery, { leakSource: '' });
                                }}
                                className="px-2 py-0.5 text-[11px] font-bold bg-rose-100 text-rose-800 border border-rose-300 rounded cursor-pointer hover:bg-rose-200"
                              >
                                × {lang === 'fa' ? 'همه لیک‌ها' : 'Clear Leak Filter'}
                              </button>
                            )}
                            {wikiranLiveMeta.facets.slice(0, 12).map((facet) => {
                              const isActive = activeLeakSourceFilter === facet.source;
                              return (
                                <button
                                  key={facet.source}
                                  type="button"
                                  onClick={() => {
                                    const nextLeak = isActive ? '' : facet.source;
                                    setActiveLeakSourceFilter(nextLeak);
                                    setSearchScopeTab('WIKIRAN');
                                    runUniversalSearchWithQuery(searchQuery, { leakSource: nextLeak });
                                  }}
                                  className={`px-2 py-0.5 text-[11px] font-medium rounded border cursor-pointer transition-colors ${
                                    isActive
                                      ? 'bg-indigo-700 text-white border-indigo-700 font-bold'
                                      : 'bg-white text-indigo-950 border-indigo-200 hover:bg-indigo-100'
                                  }`}
                                >
                                  {facet.label}{' '}
                                  <span className="font-mono-tabular font-bold ms-0.5">
                                    ({facet.amount.toLocaleString()})
                                  </span>
                                </button>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    )}

                    <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
                      <div className="px-4 sm:px-6 py-3 bg-indigo-50/70 border-b border-indigo-100 flex flex-wrap items-center justify-between gap-3 text-xs text-indigo-950 font-medium">
                        <div className="flex flex-wrap items-center gap-2.5">
                          <span>
                            {lang === 'fa'
                              ? `تعداد نتایج نمایش‌داده‌شده (ویکی‌ایران + اوفک + OpenSanctions): ${scopedResults.length}`
                              : `Showing ${scopedResults.length} matching records across WikIran + OFAC + OpenSanctions offline`}
                          </span>
                          {(filterDateFrom || filterDateTo) && (
                            <span className="px-2 py-0.5 text-[11px] font-mono-tabular font-semibold bg-amber-50 text-amber-800 border border-amber-300 rounded">
                              {filterDateFrom || '…'} → {filterDateTo || '…'}
                            </span>
                          )}
                          <span className="hidden md:inline font-mono-tabular text-[11px] text-indigo-700/80">
                            fts_archive JOIN (ofac_entities, opensanctions_entities, articles, publications, csv_row_content)
                          </span>
                        </div>
                        <button
                          type="button"
                          disabled={scopedResults.length === 0}
                          onClick={() => {
                            const csvEscape = (v: unknown) =>
                              `"${String(v ?? '').replace(/"/g, '""')}"`;
                            const headers = [
                              'Record_Type',
                              'ID',
                              'Title',
                              'Publication_Date',
                              'Category',
                              'Organizations_or_Countries',
                              'OFAC_List',
                              'OFAC_Programs',
                              'OFAC_Aliases',
                              'Summary',
                              'Matched_Excerpt',
                              'Source_URL',
                            ];
                            const rows = scopedResults.map((row) => [
                              row.record_type || '',
                              (row as Record<string, unknown>).ofac_ent_num || row.id || '',
                              row.title || '',
                              row.publication_date || '',
                              (isRtl ? row.category_fa : row.category_en) || '',
                              row.organizations || '',
                              (row as Record<string, unknown>).ofac_list_source || '',
                              String((row as Record<string, unknown>).ofac_programs || '').replace(/\]\s*\[/g, '; '),
                              (row as Record<string, unknown>).ofac_aliases || '',
                              row.short_description || '',
                              (row as Record<string, unknown>).matched_excerpt ||
                                (row as Record<string, unknown>).editorial_content ||
                                '',
                              row.source_url || '',
                            ]);
                            const csvContent =
                              '\uFEFF' +
                              [headers.join(','), ...rows.map((r) => r.map(csvEscape).join(','))].join(
                                '\r\n'
                              );
                            const blob = new Blob([csvContent], {
                              type: 'text/csv;charset=utf-8',
                            });
                            const url = URL.createObjectURL(blob);
                            const a = document.createElement('a');
                            const dateStamp = new Date().toISOString().slice(0, 10);
                            const qSlug = searchQuery
                              .trim()
                              .toLowerCase()
                              .replace(/[^a-z0-9]+/g, '_')
                              .replace(/^_|_$/g, '')
                              .slice(0, 24);
                            const dateRangeSlug =
                              filterDateFrom || filterDateTo
                                ? `_${filterDateFrom || 'start'}_to_${filterDateTo || 'latest'}`
                                : '';
                            a.href = url;
                            a.download = `wikiran_ofac_screening${qSlug ? `_${qSlug}` : ''}${dateRangeSlug}_${dateStamp}.csv`;
                            document.body.appendChild(a);
                            a.click();
                            setTimeout(() => {
                              document.body.removeChild(a);
                              URL.revokeObjectURL(url);
                            }, 250);
                            setBannerMessage({
                              text:
                                lang === 'fa'
                                  ? `خروجی سریع CSV برای ${scopedResults.length} نتیجه استعلام (ویکی‌ایران + اوفک) دانلود شد.`
                                  : `Quick Export complete: Downloaded ${scopedResults.length} filtered screening results (WikIran + OFAC) as CSV.`,
                              type: 'info',
                            });
                          }}
                          className="px-3.5 py-1.5 text-xs font-bold text-white bg-emerald-700 hover:bg-emerald-800 disabled:bg-slate-300 disabled:text-slate-500 disabled:cursor-not-allowed rounded-md transition-colors inline-flex items-center gap-1.5 cursor-pointer shadow-2xs shrink-0"
                        >
                          <Download className="w-3.5 h-3.5 shrink-0" />
                          <span>
                            {lang === 'fa'
                              ? `خروجی سریع CSV (${scopedResults.length} نتیجه)`
                              : `Quick Export CSV (${scopedResults.length})`}
                          </span>
                        </button>
                      </div>
                      <div className="overflow-x-auto">
                        <table className="w-full text-sm text-start border-collapse">
                          <thead>
                            <tr className="border-b border-slate-200 bg-slate-50/60 text-xs text-slate-500">
                              <th className="py-3 px-4 sm:px-6 text-start font-medium">{t.colTitle}</th>
                              <th className="py-3 px-4 text-start font-medium">{t.colDate}</th>
                              <th className="py-3 px-4 text-start font-medium">{t.colCategory}</th>
                              <th className="py-3 px-4 sm:px-6 text-start font-medium">{t.colSource}</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-200">
                            {scopedResults.map((row, idx) => {
                              const isOfac = row.record_type === 'OFAC_SANCTION';
                              const isOs = row.record_type === 'OPENSANCTIONS';
                              const isWikiranLive = row.record_type === 'WIKIRAN_LIVE';
                              const isWikiranDoc = row.record_type === 'WIKIRAN_DOC';
                              const wDocType = String((row as Record<string, unknown>).wikiran_doc_type || '');
                              const wDocBadgeLabel =
                                wDocType === 'FRONT_COMPANY'
                                  ? 'Front Company'
                                  : wDocType === 'VESSEL'
                                  ? 'Vessel'
                                  : wDocType === 'LEAKED_EMAIL'
                                  ? 'Leaked Email'
                                  : wDocType === 'LEAKED_FILE'
                                  ? 'Leaked File'
                                  : wDocType === 'LEAKED_CSV'
                                  ? 'WikIran CSV'
                                  : 'WikIran Doc';
                              const ofacList = String((row as Record<string, unknown>).ofac_list_source || 'SDN');
                              const ofacType = String((row as Record<string, unknown>).ofac_sdn_type || '');
                              const ofacEntNum = (row as Record<string, unknown>).ofac_ent_num;
                              const osSchema = String((row as Record<string, unknown>).os_schema || '');
                              const osId = String((row as Record<string, unknown>).os_id || '');
                              const ofacProgramsClean = String(
                                (row as Record<string, unknown>).ofac_programs || ''
                              )
                                .replace(/\]\s*\[/g, '; ')
                                .replace(/^\[|\]$/g, '');
                              const ofacAliases = String(
                                (row as Record<string, unknown>).ofac_aliases || ''
                              );
                              const ofacAddresses = String(
                                (row as Record<string, unknown>).ofac_addresses || ''
                              );

                              const summaryText = String(row.short_description || '');
                              const excerptText = String(
                                (row as Record<string, unknown>).matched_excerpt ||
                                  (row as Record<string, unknown>).editorial_content ||
                                  ''
                              );
                              const showDistinctExcerpt =
                                !isOfac &&
                                Boolean(searchQuery.trim()) &&
                                Boolean(excerptText) &&
                                excerptText !== summaryText;

                              return (
                                <tr
                                  key={`${row.record_type}-${row.id}-${idx}`}
                                  className={
                                    isOfac
                                      ? 'bg-rose-50/35 hover:bg-rose-50/70 transition-colors'
                                      : isOs
                                      ? 'bg-amber-50/35 hover:bg-amber-50/70 transition-colors'
                                      : isWikiranLive
                                      ? 'bg-indigo-50/35 hover:bg-indigo-50/70 transition-colors'
                                      : isWikiranDoc
                                      ? 'bg-sky-50/25 hover:bg-sky-50/60 transition-colors'
                                      : 'hover:bg-slate-50 transition-colors'
                                  }
                                >
                                  <td className="py-3.5 px-4 sm:px-6 space-y-1.5">
                                    <div className="flex flex-wrap items-center gap-2">
                                      {isOfac && (
                                        <span
                                          className={`px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider rounded ${
                                            ofacList === 'SDN'
                                              ? 'bg-rose-700 text-white'
                                              : 'bg-amber-700 text-white'
                                          }`}
                                        >
                                          OFAC {ofacList}
                                        </span>
                                      )}
                                      {isOs && (
                                        <span className="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider rounded bg-amber-600 text-white">
                                          OpenSanctions
                                        </span>
                                      )}
                                      {isWikiranLive && (
                                        <span className="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider rounded bg-indigo-700 text-white">
                                          WikIran Live
                                        </span>
                                      )}
                                      {(isWikiranLive || isWikiranDoc) && (
                                        <span
                                          className={`px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider rounded ${
                                            wDocType === 'FRONT_COMPANY'
                                              ? 'bg-purple-700 text-white'
                                              : wDocType === 'VESSEL'
                                              ? 'bg-sky-700 text-white'
                                              : 'bg-slate-700 text-white'
                                          }`}
                                        >
                                          {wDocBadgeLabel}
                                        </span>
                                      )}
                                      {isOs && osSchema && (
                                        <span className="px-1.5 py-0.5 text-[10px] font-semibold uppercase bg-amber-100 text-amber-950 rounded">
                                          {osSchema}
                                        </span>
                                      )}
                                      {isOs && osId && (
                                        <span className="text-[10px] font-mono-tabular text-slate-500">
                                          {osId}
                                        </span>
                                      )}
                                      {isOfac && ofacType && (
                                        <span className="px-1.5 py-0.5 text-[10px] font-semibold uppercase bg-slate-200 text-slate-800 rounded">
                                          {ofacType}
                                        </span>
                                      )}
                                      {isOfac && ofacEntNum ? (
                                        <span className="text-[11px] font-mono-tabular text-rose-800 font-semibold">
                                          ID #{String(ofacEntNum)}
                                        </span>
                                      ) : null}
                                      <span className="font-semibold text-slate-900">
                                        {highlightSearchTerms(String(row.title || ''), searchQuery)}
                                      </span>
                                    </div>

                                    {isOfac ? (
                                      <div className="space-y-1 text-xs">
                                        {ofacProgramsClean && (
                                          <div className="flex flex-wrap items-center gap-1">
                                            {ofacProgramsClean
                                              .split(';')
                                              .map((p) => p.trim())
                                              .filter(Boolean)
                                              .map((prog) => (
                                                <span
                                                  key={prog}
                                                  className="px-1.5 py-0.5 text-[10px] font-mono-tabular font-bold bg-rose-100 text-rose-900 border border-rose-200 rounded"
                                                >
                                                  {highlightSearchTerms(prog, searchQuery)}
                                                </span>
                                              ))}
                                          </div>
                                        )}
                                        {ofacAliases && (
                                          <div className="text-slate-700 leading-relaxed">
                                            <span className="font-semibold text-slate-900 me-1">
                                              {lang === 'fa' ? 'اسامی مستعار (AKA):' : 'Aliases (AKA):'}
                                            </span>
                                            {highlightSearchTerms(ofacAliases.slice(0, 260), searchQuery)}
                                          </div>
                                        )}
                                        {ofacAddresses && (
                                          <div className="text-slate-600 leading-relaxed">
                                            <span className="font-semibold text-slate-800 me-1">
                                              {lang === 'fa' ? 'نشانی‌ها:' : 'Addresses:'}
                                            </span>
                                            {highlightSearchTerms(ofacAddresses.slice(0, 220), searchQuery)}
                                          </div>
                                        )}
                                      </div>
                                    ) : (
                                      <>
                                        <div className="text-xs text-slate-700 leading-relaxed">
                                          {highlightSearchTerms(summaryText, searchQuery)}
                                        </div>
                                        {showDistinctExcerpt && (
                                          <div className="text-xs text-slate-800 bg-amber-50/80 border-s-2 border-amber-400 ps-2.5 py-1 rounded-e leading-relaxed">
                                            <span className="font-semibold text-slate-600 me-1">
                                              {lang === 'fa' ? 'گزیده متن منطبق:' : 'Matched Excerpt:'}
                                            </span>
                                            {highlightSearchTerms(excerptText.slice(0, 320), searchQuery)}
                                          </div>
                                        )}
                                      </>
                                    )}

                                    <div
                                      className={`text-xs font-semibold ${
                                        isOfac ? 'text-rose-800' : 'text-indigo-700'
                                      }`}
                                    >
                                      <span>{String(row.record_type || '')}</span>
                                      {row.organizations ? (
                                        <>
                                          <span aria-hidden="true"> · </span>
                                          <span>
                                            {highlightSearchTerms(
                                              String(row.organizations),
                                              searchQuery
                                            )}
                                          </span>
                                        </>
                                      ) : null}
                                    </div>
                                  </td>
                                  <td className="py-3.5 px-4 font-mono-tabular text-xs text-slate-700 whitespace-nowrap">
                                    {String(row.publication_date || '')}
                                  </td>
                                  <td className="py-3.5 px-4 text-xs text-slate-700">
                                    {highlightSearchTerms(
                                      String(isRtl ? row.category_fa : row.category_en).replace(
                                        /\]\s*\[/g,
                                        '; '
                                      ),
                                      searchQuery
                                    )}
                                  </td>
                                  <td className="py-3.5 px-4 sm:px-6 text-xs">
                                    <a
                                      href={String(row.source_url || '#')}
                                      target="_blank"
                                      rel="noreferrer"
                                      className={`${
                                        isOfac
                                          ? 'text-rose-800 hover:text-rose-950'
                                          : 'text-indigo-700 hover:text-indigo-950'
                                      } underline inline-flex items-center gap-1 font-mono-tabular break-all`}
                                    >
                                      <span>
                                        {highlightSearchTerms(
                                          String(row.source_url || '')
                                            .replace('https://wikiran.org', '')
                                            .replace(
                                              'https://sanctionslistservice.ofac.treas.gov',
                                              'OFAC SLS'
                                            ),
                                          searchQuery
                                        )}
                                      </span>
                                      <ExternalLink className="w-3 h-3 shrink-0" />
                                    </a>
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </div>
                );
              })()}
            </div>
          )}

          {/* 3. ARTICLES */}
          {activeNav === 'articles' && (
            <div className="space-y-6">
              {selectedArticle && (
                <div className="bg-white border border-blue-300 rounded-lg p-4 sm:p-6 space-y-4">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div className="space-y-1">
                      <div className="text-xs text-blue-700 font-medium">
                        <span>{selectedArticle.subtitle}</span>
                        <span aria-hidden="true"> · </span>
                        <span className="font-mono-tabular">
                          {selectedArticle.publication_date}
                        </span>
                        <span aria-hidden="true"> · </span>
                        <span>{selectedArticle.author}</span>
                      </div>
                      <h2 className="text-lg sm:text-xl font-bold text-slate-900">
                        {selectedArticle.title}
                      </h2>
                    </div>
                    <button
                      onClick={() => setSelectedArticle(null)}
                      className="px-3 py-1.5 text-xs font-semibold text-slate-700 bg-slate-100 rounded hover:bg-slate-200 cursor-pointer"
                    >
                      {lang === 'fa' ? 'بستن متن کامل' : 'Close Reader'}
                    </button>
                  </div>
                  <p className="text-sm text-slate-800 leading-relaxed whitespace-pre-line">
                    {selectedArticle.editorial_content}
                  </p>
                  <div className="pt-3 border-t border-slate-200 flex flex-wrap items-center justify-between gap-4 text-xs text-slate-500">
                    <div>
                      <span>Organizations: {selectedArticle.organizations_list || 'N/A'}</span>
                      <span aria-hidden="true"> · </span>
                      <span>Tags: {selectedArticle.tags_list || 'N/A'}</span>
                    </div>
                    <div className="font-mono-tabular">
                      SHA-256: {selectedArticle.content_hash.slice(0, 16)}… · v
                      {selectedArticle.record_version}
                    </div>
                  </div>
                </div>
              )}

              <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm text-start border-collapse">
                    <thead>
                      <tr className="border-b border-slate-200 bg-blue-50/60 text-xs text-blue-950">
                        <th className="py-3 px-4 sm:px-6 text-start font-semibold">{t.colTitle}</th>
                        <th className="py-3 px-4 text-start font-semibold">{t.colDate}</th>
                        <th className="py-3 px-4 text-start font-semibold">{t.colCategory}</th>
                        <th className="py-3 px-4 text-start font-semibold">{t.colVersion}</th>
                        <th className="py-3 px-4 sm:px-6 text-start font-semibold">
                          {t.colSource}
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200">
                      {data.articles.map((art) => (
                        <tr key={art.id} className="hover:bg-blue-50/30 transition-colors">
                          <td className="py-4 px-4 sm:px-6 space-y-1">
                            <button
                              onClick={() => setSelectedArticle(art)}
                              className="font-semibold text-blue-900 hover:underline text-start cursor-pointer"
                            >
                              {art.title}
                            </button>
                            <p className="text-xs text-slate-600">{art.summary}</p>
                            <div className="text-xs text-slate-500">
                              <span>{art.author}</span>
                              <span aria-hidden="true"> · </span>
                              <span>{art.organizations_list}</span>
                            </div>
                          </td>
                          <td className="py-4 px-4 font-mono-tabular text-xs text-slate-700 whitespace-nowrap">
                            {art.publication_date}
                          </td>
                          <td className="py-4 px-4 text-xs text-slate-700">
                            {isRtl ? art.categories_fa : art.categories_en}
                          </td>
                          <td className="py-4 px-4 font-mono-tabular text-xs text-emerald-700 font-medium">
                            v{art.record_version} ({art.extraction_status})
                          </td>
                          <td className="py-4 px-4 sm:px-6 text-xs font-mono-tabular">
                            <a
                              href={art.source_url}
                              target="_blank"
                              rel="noreferrer"
                              className="text-blue-700 hover:text-blue-950 underline inline-flex items-center gap-1"
                            >
                              <span>/document/articles/{art.original_pub_id.slice(0, 8)}…</span>
                              <ExternalLink className="w-3 h-3 shrink-0" />
                            </a>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* 4. PUBLICATION CATALOGUE */}
          {activeNav === 'publications' && (
            <div className="space-y-4">
              <div className="bg-white border border-teal-200 rounded-lg divide-y divide-slate-200">
                {data.publications.map((pub) => (
                  <div
                    key={pub.id}
                    className="p-4 sm:p-6 space-y-2 hover:bg-teal-50/20 transition-colors"
                  >
                    <div className="flex flex-wrap items-baseline justify-between gap-2">
                      <h3 className="text-base font-bold text-teal-950">{pub.title}</h3>
                      <span className="text-xs font-mono-tabular text-teal-700 font-medium">
                        {pub.publication_date} · /leak/{pub.original_pub_id}
                      </span>
                    </div>
                    {pub.native_title && (
                      <div className="text-xs font-medium text-slate-600">{pub.native_title}</div>
                    )}
                    <p className="text-sm text-slate-700 leading-relaxed">{pub.description}</p>
                    <div className="pt-2 flex flex-wrap items-center justify-between gap-4 text-xs text-slate-500">
                      <div>
                        <span className="font-medium text-teal-800">
                          {isRtl ? pub.categories_fa : pub.categories_en}
                        </span>
                        <span aria-hidden="true"> · </span>
                        <span>
                          Inventory:{' '}
                          {pub.inventory
                            ?.map((i) => `${i.data_type} (${i.reported_count_label})`)
                            .join(' / ')}
                        </span>
                      </div>
                      <a
                        href={pub.source_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-teal-700 underline hover:text-teal-950 inline-flex items-center gap-1 font-mono-tabular break-all"
                      >
                        <span>{pub.source_url}</span>
                        <ExternalLink className="w-3 h-3 shrink-0" />
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 5. ORGANIZATIONS */}
          {activeNav === 'organizations' && (
            <div className="bg-white border border-amber-200 rounded-lg overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-start border-collapse">
                  <thead>
                    <tr className="border-b border-amber-200 bg-amber-50/60 text-xs text-amber-950">
                      <th className="py-3 px-4 sm:px-6 text-start font-semibold">
                        Organization / Institution
                      </th>
                      <th className="py-3 px-4 text-start font-semibold">Native Name</th>
                      <th className="py-3 px-4 text-start font-semibold">Classification</th>
                      <th className="py-3 px-4 text-end font-semibold">Linked Articles</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    {data.organizations.map((org) => (
                      <tr key={org.id} className="hover:bg-amber-50/20">
                        <td className="py-4 px-4 sm:px-6 space-y-1">
                          <div className="font-semibold text-slate-900">
                            {org.name} {org.acronym ? `(${org.acronym})` : ''}
                          </div>
                          <div className="text-xs text-slate-600">{org.description}</div>
                        </td>
                        <td className="py-4 px-4 text-xs text-slate-700">{org.native_name}</td>
                        <td className="py-4 px-4 text-xs font-mono-tabular text-amber-800 font-medium">
                          {org.org_type}
                        </td>
                        <td className="py-4 px-4 text-end font-mono-tabular text-sm font-bold text-slate-900">
                          {org.linked_articles_count}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* 6. CATEGORIES */}
          {activeNav === 'categories' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {data.categories.map((cat) => (
                <div
                  key={cat.id}
                  className="bg-white border border-purple-200 rounded-lg p-5 sm:p-6 flex flex-col justify-between space-y-4 hover:border-purple-400 transition-colors"
                >
                  <div className="space-y-1">
                    <div className="text-base font-bold text-purple-950">
                      {isRtl ? cat.name_fa : cat.name_en}
                    </div>
                    <div className="text-xs text-purple-700 font-medium">
                      {isRtl ? cat.name_en : cat.name_fa} · slug: {cat.slug}
                    </div>
                    <p className="text-sm text-slate-700 pt-1">{cat.description}</p>
                  </div>
                  <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-600">
                    <span className="font-mono-tabular">
                      {cat.article_count} Articles · {cat.publication_count} Catalogues
                    </span>
                    <button
                      onClick={() => {
                        setFilterCategory(cat.slug);
                        setActiveNav('search');
                      }}
                      className="font-semibold text-purple-800 hover:underline cursor-pointer"
                    >
                      {lang === 'fa' ? 'فیلتر در جستجو ←' : 'Filter in Search →'}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* 7. EXPORT REPORTS & STYLISH HUMAN-READABLE DATA CONVERTER */}
          {activeNav === 'exports' && (
            <div className="space-y-8">
              {/* SECTION 1 (TOP): EXPORT REPORT WIZARD (OFAC SANCTIONS + WIKIRAN EXCEL BUILDER) */}
              <section className="bg-white border-2 border-indigo-300 rounded-xl overflow-hidden shadow-xs">
                <div className="bg-slate-900 text-white px-5 sm:px-6 py-5 flex flex-wrap items-center justify-between gap-4 border-b border-slate-800">
                  <div className="space-y-1">
                    <div className="text-xs font-bold text-amber-400 uppercase tracking-wider">
                      {lang === 'fa'
                        ? 'گزارش‌ساز رسمی اکسل (.XLSX) — اوفک + ویکی‌ایران'
                        : 'EXPORT REPORT WIZARD · OFAC + WIKIRAN EXCEL (.XLSX) BUILDER'}
                    </div>
                    <h2 className="text-base sm:text-lg font-bold text-white">
                      {lang === 'fa'
                        ? 'ساخت و دانلود گزارش اکسل سفارشی (تحریم‌های ایران اوفک، کل اوفک و آرشیو ویکی‌ایران)'
                        : 'Export Styled Excel (.xlsx) Reports — Choose OFAC & WikIran Sheets'}
                    </h2>
                    <p className="text-xs text-slate-300 max-w-3xl">
                      {lang === 'fa'
                        ? 'دقیقاً انتخاب کنید کدام شیت‌ها (لیست تحریم‌های ایران اوفک، کل دیتاست اوفک، مقالات یا انتشارات ویکی‌ایران) با بازه زمانی دلخواه در فایل اکسل قرار بگیرند.'
                        : 'Select which formatted worksheets (OFAC Iran Sanctions, Full OFAC SDN + Consolidated, WikIran Articles, Publications, Organizations, or Tags) to include in one clean Excel (.xlsx) report.'}
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2 shrink-0">
                    <button
                      type="button"
                      onClick={() =>
                        setWizardEntities(['ofac_iran', 'opensanctions_iran', 'articles', 'publications'])
                      }
                      className="px-3 py-1.5 text-xs font-semibold text-white bg-rose-700 hover:bg-rose-600 rounded-md transition-colors cursor-pointer"
                    >
                      {lang === 'fa' ? 'پکیج کامل ایران (OFAC + OpenSanctions + ویکی‌ایران)' : 'Full Iran Bundle'}
                    </button>
                    <button
                      type="button"
                      onClick={() => setWizardEntities(['ofac_iran', 'opensanctions_iran'])}
                      className="px-3 py-1.5 text-xs font-semibold text-slate-200 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-md transition-colors cursor-pointer"
                    >
                      {lang === 'fa' ? 'فقط تحریم‌های ایران' : 'Iran Sanctions Only'}
                    </button>
                    <button
                      type="button"
                      onClick={() => setWizardEntities(['ofac_all'])}
                      className="px-3 py-1.5 text-xs font-semibold text-slate-200 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-md transition-colors cursor-pointer"
                    >
                      {lang === 'fa' ? 'کل دیتاست اوفک' : 'Full OFAC'}
                    </button>
                  </div>
                </div>

                <div className="p-5 sm:p-6 space-y-5 bg-slate-50/70">
                  {/* Step 1: Select Worksheets Checkboxes (OFAC + OpenSanctions + WikIran) */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
                    {[
                      {
                        key: 'ofac_iran' as const,
                        titleEn: 'OFAC Iran-Linked Sanctions',
                        titleFa: 'تحریم‌های مرتبط با ایران اوفک (OFAC)',
                        count: data.ofac_summary?.iran_related_count ?? 0,
                        descEn:
                          'All Iran-linked SDN & Consolidated entities (IRAN, IRGC, IFSR, EO13902, EO13846)',
                        descFa:
                          'همه نهادها و افراد تحریمی مرتبط با ایران در اوفک همراه با AKA و نشانی',
                        borderColor: 'border-rose-500 bg-rose-50/70',
                        badgeColor: 'bg-rose-100 text-rose-900',
                      },
                      {
                        key: 'ofac_all' as const,
                        titleEn: 'OFAC Full Global Sanctions',
                        titleFa: 'کل دیتاست جهانی اوفک (SDN + Consolidated)',
                        count: data.ofac_summary?.total_entities ?? 0,
                        descEn:
                          'Complete U.S. Treasury SDN + Non-SDN Consolidated lists (all 8 lists)',
                        descFa: 'تمامی ۸ لیست رسمی خزانه‌داری آمریکا با تمام برنامه‌ها',
                        borderColor: 'border-red-600 bg-red-50/60',
                        badgeColor: 'bg-red-100 text-red-900',
                      },
                      {
                        key: 'opensanctions_iran' as const,
                        titleEn: 'OpenSanctions Iran-Linked',
                        titleFa: 'تحریم‌های ایران OpenSanctions (جهانی)',
                        count: data.opensanctions_summary?.iran_related_count ?? 0,
                        descEn:
                          'Global UN, EU, UK OFSI, US, Canada & Australia Iran-linked sanctions targets',
                        descFa: 'اهداف تحریمی مرتبط با ایران از سازمان ملل، اروپا، انگلستان و آمریکا',
                        borderColor: 'border-amber-500 bg-amber-50/70',
                        badgeColor: 'bg-amber-100 text-amber-950',
                      },
                      {
                        key: 'opensanctions_all' as const,
                        titleEn: 'OpenSanctions Global All',
                        titleFa: 'کل دیتاست جهانی OpenSanctions',
                        count: data.opensanctions_summary?.total_entities ?? 0,
                        descEn:
                          'Full consolidated global sanctions targets across all international lists',
                        descFa: 'کل رکوردهای تجمیعی تحریم‌های بین‌المللی در OpenSanctions',
                        borderColor: 'border-orange-500 bg-orange-50/60',
                        badgeColor: 'bg-orange-100 text-orange-950',
                      },
                      {
                        key: 'articles' as const,
                        titleEn: 'WikIran Articles',
                        titleFa: 'مقالات تحلیلی ویکی‌ایران (Articles)',
                        count: data.stats.articles_count,
                        descEn: 'Titles, dates, authors, categories, summaries & source URLs',
                        descFa: 'عنوان، تاریخ انتشار، نویسنده، دسته‌بندی، خلاصه و لینک منبع',
                        borderColor: 'border-blue-500 bg-blue-50/70',
                        badgeColor: 'bg-blue-100 text-blue-900',
                      },
                      {
                        key: 'publications' as const,
                        titleEn: 'WikIran Publications',
                        titleFa: 'فهرست انتشارات ویکی‌ایران (Publications)',
                        count: data.stats.publications_count,
                        descEn: 'Catalogue titles, descriptions & file inventory metadata',
                        descFa: 'عناوین فهرست انتشارات، توضیحات و متادیتای موجودی فایل‌ها',
                        borderColor: 'border-teal-500 bg-teal-50/70',
                        badgeColor: 'bg-teal-100 text-teal-900',
                      },
                      {
                        key: 'organizations' as const,
                        titleEn: 'WikIran Organizations',
                        titleFa: 'سازمان‌ها و نهادها (Organizations)',
                        count: data.stats.organizations_count,
                        descEn: 'Organization names, native names, acronyms & linked articles',
                        descFa: 'نام سازمان، نام فارسی، اختصار، نوع نهاد و تعداد مقالات مرتبط',
                        borderColor: 'border-amber-500 bg-amber-50/70',
                        badgeColor: 'bg-amber-100 text-amber-950',
                      },
                      {
                        key: 'tags' as const,
                        titleEn: 'WikIran Tags',
                        titleFa: 'برچسب‌ها و کلیدواژه‌ها (Tags)',
                        count: data.tags?.length || 10,
                        descEn: 'Tag slugs, keyword labels, linked article counts & titles',
                        descFa: 'کلیدواژه‌ها، شناسه برچسب، تعداد و عناوین مقالات مرتبط',
                        borderColor: 'border-purple-500 bg-purple-50/70',
                        badgeColor: 'bg-purple-100 text-purple-950',
                      },
                    ].map((ent) => {
                      const isSelected = wizardEntities.includes(ent.key);
                      return (
                        <label
                          key={ent.key}
                          onClick={() => toggleWizardEntity(ent.key)}
                          className={`rounded-xl p-4 border-2 transition-all cursor-pointer flex flex-col justify-between space-y-2.5 select-none ${
                            isSelected
                              ? `${ent.borderColor} shadow-xs`
                              : 'bg-white border-slate-200 hover:border-slate-300 opacity-85'
                          }`}
                        >
                          <div className="space-y-1.5">
                            <div className="flex items-center justify-between gap-2">
                              <input
                                type="checkbox"
                                checked={isSelected}
                                onChange={() => {}}
                                className="w-4 h-4 accent-indigo-600 rounded cursor-pointer"
                              />
                              <span
                                className={`text-xs font-mono-tabular font-bold px-2 py-0.5 rounded ${ent.badgeColor}`}
                              >
                                {ent.count.toLocaleString()} {lang === 'fa' ? 'رکورد' : 'records'}
                              </span>
                            </div>
                            <div className="text-sm font-bold text-slate-900">
                              {lang === 'fa' ? ent.titleFa : ent.titleEn}
                            </div>
                            <p className="text-xs text-slate-600 leading-relaxed">
                              {lang === 'fa' ? ent.descFa : ent.descEn}
                            </p>
                          </div>
                          <div className="text-[11px] font-semibold text-indigo-800">
                            {isSelected
                              ? lang === 'fa'
                                ? '✓ در فایل اکسل قرار می‌گیرد'
                                : '✓ Included as Excel Sheet'
                              : lang === 'fa'
                              ? 'برای افزودن کلیک کنید'
                              : 'Click to include'}
                          </div>
                        </label>
                      );
                    })}
                  </div>

                  {/* Step 2: Date Range Filter for WikIran Articles & Publications */}
                  {(() => {
                    const filterByWizardDates = (pubDate: string) => {
                      if (!wizardDateFrom && !wizardDateTo) return true;
                      const d = (pubDate || '').trim().slice(0, 10);
                      if (!d) return false;
                      if (wizardDateFrom && d < wizardDateFrom) return false;
                      if (wizardDateTo && d > wizardDateTo) return false;
                      return true;
                    };
                    const filteredArticlesCount = data.articles.filter((a) =>
                      filterByWizardDates(a.publication_date)
                    ).length;
                    const filteredPubsCount = data.publications.filter((p) =>
                      filterByWizardDates(p.publication_date)
                    ).length;

                    const exportParams = new URLSearchParams();
                    exportParams.set('entities', wizardEntities.join(','));
                    if (wizardDateFrom) exportParams.set('date_from', wizardDateFrom);
                    if (wizardDateTo) exportParams.set('date_to', wizardDateTo);
                    const wizardDownloadHref = `/api/export/xlsx?${exportParams.toString()}`;

                    return (
                      <>
                        <div className="bg-white border border-slate-200 rounded-lg p-4 space-y-3">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <div className="flex items-center gap-2 text-xs font-bold text-slate-800">
                              <Calendar className="w-4 h-4 text-indigo-600 shrink-0" />
                              <span>
                                {lang === 'fa'
                                  ? 'بازه زمانی اختیاری (فیلتر تاریخ انتشار برای مقالات و انتشارات ویکی‌ایران):'
                                  : 'Optional Date Range Filter (Applies to WikIran Articles & Publications):'}
                              </span>
                            </div>
                            <div className="flex flex-wrap items-center gap-1.5">
                              <button
                                type="button"
                                onClick={() => {
                                  setWizardDateFrom('2026-01-01');
                                  setWizardDateTo('2026-12-31');
                                }}
                                className="px-2.5 py-1 text-[11px] font-semibold bg-slate-100 hover:bg-indigo-50 text-slate-700 hover:text-indigo-800 border border-slate-300 rounded cursor-pointer"
                              >
                                2026
                              </button>
                              <button
                                type="button"
                                onClick={() => {
                                  setWizardDateFrom('2025-01-01');
                                  setWizardDateTo('2026-12-31');
                                }}
                                className="px-2.5 py-1 text-[11px] font-semibold bg-slate-100 hover:bg-indigo-50 text-slate-700 hover:text-indigo-800 border border-slate-300 rounded cursor-pointer"
                              >
                                2025–2026
                              </button>
                              {(wizardDateFrom || wizardDateTo) && (
                                <button
                                  type="button"
                                  onClick={() => {
                                    setWizardDateFrom('');
                                    setWizardDateTo('');
                                  }}
                                  className="px-2.5 py-1 text-[11px] font-semibold bg-red-50 hover:bg-red-100 text-red-700 border border-red-200 rounded cursor-pointer"
                                >
                                  {lang === 'fa' ? 'پاک کردن بازه' : 'Clear Dates'}
                                </button>
                              )}
                            </div>
                          </div>

                          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 items-end">
                            <div className="space-y-1">
                              <label className="block text-[11px] font-semibold text-slate-600">
                                {lang === 'fa' ? 'از تاریخ (Start Date):' : 'Start Date (From):'}
                              </label>
                              <input
                                type="date"
                                value={wizardDateFrom}
                                onChange={(e) => setWizardDateFrom(e.target.value)}
                                className="w-full px-3 py-2 text-xs font-mono-tabular border border-slate-300 rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-indigo-600"
                              />
                            </div>
                            <div className="space-y-1">
                              <label className="block text-[11px] font-semibold text-slate-600">
                                {lang === 'fa' ? 'تا تاریخ (End Date):' : 'End Date (To):'}
                              </label>
                              <input
                                type="date"
                                value={wizardDateTo}
                                onChange={(e) => setWizardDateTo(e.target.value)}
                                className="w-full px-3 py-2 text-xs font-mono-tabular border border-slate-300 rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-indigo-600"
                              />
                            </div>
                            <div className="px-3 py-2 rounded-md bg-indigo-50/70 border border-indigo-200 text-xs text-indigo-950 font-medium">
                              {wizardDateFrom || wizardDateTo ? (
                                <span>
                                  {lang === 'fa'
                                    ? `مطابق بازه زمانی: ${filteredArticlesCount} مقاله · ${filteredPubsCount} انتشار`
                                    : `Matching Date Range: ${filteredArticlesCount} Articles · ${filteredPubsCount} Publications`}
                                </span>
                              ) : (
                                <span className="text-slate-600">
                                  {lang === 'fa'
                                    ? 'همه تاریخ‌ها شامل می‌شوند (بدون محدودیت زمانی)'
                                    : 'All dates included (no date restriction)'}
                                </span>
                              )}
                            </div>
                          </div>
                        </div>

                        {/* Step 3: Summary & Generate Custom Excel Button */}
                        <div className="bg-white border border-indigo-200 rounded-lg p-4 flex flex-wrap items-center justify-between gap-4">
                          <div className="space-y-1">
                            <div className="text-xs font-bold text-slate-800">
                              {lang === 'fa'
                                ? `شیت‌های انتخاب‌شده برای ساخت فایل اکسل (${wizardEntities.length} شیت):`
                                : `Selected Worksheets for Custom Excel Report (${wizardEntities.length} sheets):`}
                            </div>
                            <div className="flex flex-wrap items-center gap-1.5">
                              {wizardEntities.length > 0 ? (
                                <>
                                  {wizardEntities.map((key) => (
                                    <span
                                      key={key}
                                      className={`px-2.5 py-0.5 text-xs font-mono-tabular font-semibold rounded border uppercase ${
                                        key.startsWith('ofac')
                                          ? 'bg-rose-100 text-rose-900 border-rose-300'
                                          : 'bg-indigo-100 text-indigo-900 border-indigo-300'
                                      }`}
                                    >
                                      {key.replace('_', ' ')}
                                    </span>
                                  ))}
                                  {(wizardDateFrom || wizardDateTo) && (
                                    <span className="px-2.5 py-0.5 text-xs font-mono-tabular font-semibold bg-amber-100 text-amber-950 rounded border border-amber-300">
                                      {wizardDateFrom || '…'} → {wizardDateTo || '…'}
                                    </span>
                                  )}
                                </>
                              ) : (
                                <span className="text-xs text-red-600 font-semibold">
                                  {lang === 'fa'
                                    ? 'لطفاً حداقل یک بخش را انتخاب کنید.'
                                    : 'Please select at least one data entity above.'}
                                </span>
                              )}
                            </div>
                          </div>

                          {wizardEntities.length > 0 ? (
                            <a
                              href={wizardDownloadHref}
                              className="px-5 py-2.5 text-xs sm:text-sm font-bold text-white bg-indigo-700 hover:bg-indigo-800 rounded-lg transition-colors inline-flex items-center gap-2 shadow-xs"
                            >
                              <FileSpreadsheet className="w-4 h-4 shrink-0" />
                              <span>
                                {lang === 'fa'
                                  ? `دانلود گزارش اکسل سفارشی (${wizardEntities.length} شیت)`
                                  : `Download Custom Excel Report (${wizardEntities.length} Sheets)`}
                              </span>
                            </a>
                          ) : (
                            <button
                              type="button"
                              disabled
                              className="px-5 py-2.5 text-xs sm:text-sm font-bold text-slate-400 bg-slate-200 rounded-lg cursor-not-allowed"
                            >
                              {lang === 'fa'
                                ? 'حداقل یک بخش را انتخاب کنید'
                                : 'Select at Least 1 Entity'}
                            </button>
                          )}
                        </div>
                      </>
                    );
                  })()}
                </div>
              </section>

              {/* SECTION 2: STYLISH HUMAN-READABLE DATA CONVERTER & VIEWER (OFAC + UPLOADED CSV -> EXCEL) */}
              <section className="bg-white border-2 border-emerald-300 rounded-xl overflow-hidden shadow-xs">
                <div className="bg-gradient-to-r from-slate-900 via-emerald-950 to-slate-900 text-white px-5 sm:px-6 py-5 flex flex-wrap items-center justify-between gap-4">
                  <div className="space-y-1">
                    <div className="text-xs font-bold text-emerald-300 uppercase tracking-wider">
                      {lang === 'fa'
                        ? 'مبدل خوانا و هوشمند فایل‌های خام CSV / OFAC به جدول انسانی و اکسل'
                        : 'HUMAN-READABLE DATA CONVERTER · RAW CSV / OFAC TO STYLED TABLE & EXCEL'}
                    </div>
                    <h3 className="text-lg font-bold text-white">
                      {lang === 'fa'
                        ? 'نمایشگر و مبدل خوانای داده‌های اوفک و فایل‌های CSV'
                        : 'Human-Readable OFAC & CSV-to-Excel Converter'}
                    </h3>
                    <p className="text-xs text-emerald-100/90 max-w-3xl leading-relaxed">
                      {lang === 'fa'
                        ? 'به‌جای باز کردن فایل‌های خام و شلوغ CSV، اینجا می‌توانید لیست تحریم‌های ایران اوفک یا هر فایل CSV دلخواه (از اوفک، ویکی‌ایران یا شیت‌های تجاری) را در یک جدول خوانا و مرتب ببینید و با یک کلیک به اکسل (.xlsx) تبدیل کنید.'
                        : 'Inspect OFAC Iran sanctions or drop any raw .CSV spreadsheet to instantly transform ugly raw CSV text into a clean, color-coded human-readable table and download it as a formatted Excel (.xlsx) workbook.'}
                    </p>
                  </div>

                  <div className="flex flex-wrap items-center gap-2 shrink-0">
                    <label className="px-4 py-2 text-xs font-bold text-emerald-950 bg-emerald-300 hover:bg-emerald-200 rounded-lg transition-colors inline-flex items-center gap-2 cursor-pointer shadow-xs">
                      <Upload className="w-4 h-4" />
                      <span>{t.csvUploadBtn}</span>
                      <input
                        type="file"
                        accept=".csv,text/csv"
                        onChange={(e) => {
                          setConverterTab('csv');
                          handleCsvFileUpload(e);
                        }}
                        className="hidden"
                      />
                    </label>
                    {converterTab === 'ofac_iran' ? (
                      <a
                        href="/api/export/xlsx?entities=ofac_iran"
                        className="px-4 py-2 text-xs font-bold text-white bg-rose-600 hover:bg-rose-500 border border-rose-400 rounded-lg transition-colors inline-flex items-center gap-2 shadow-xs"
                      >
                        <FileSpreadsheet className="w-4 h-4" />
                        <span>
                          {lang === 'fa'
                            ? 'دانلود کل اوفک ایران به اکسل (.xlsx)'
                            : 'Download OFAC Iran Excel (.xlsx)'}
                        </span>
                      </a>
                    ) : currentCsvDataset && currentCsvDataset.id > 0 ? (
                      <a
                        href={`/api/csv/download/${currentCsvDataset.id}`}
                        className="px-4 py-2 text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-500 border border-emerald-400 rounded-lg transition-colors inline-flex items-center gap-2 shadow-xs"
                      >
                        <FileSpreadsheet className="w-4 h-4" />
                        <span>{t.csvDownloadXlsxBtn}</span>
                      </a>
                    ) : null}
                  </div>
                </div>

                {/* Mode Switcher Tabs: Live Human-Readable OFAC Iran Viewer vs CSV File Converter */}
                <div className="px-5 py-3 bg-slate-100 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <button
                      type="button"
                      onClick={() => setConverterTab('ofac_iran')}
                      className={`px-3.5 py-1.5 text-xs font-bold rounded-md transition-colors cursor-pointer ${
                        converterTab === 'ofac_iran'
                          ? 'bg-rose-700 text-white shadow-2xs'
                          : 'bg-white text-slate-700 border border-slate-300 hover:bg-rose-50'
                      }`}
                    >
                      {lang === 'fa'
                        ? `جدول خوانای اوفک ایران (${(data.ofac_summary?.iran_related_count ?? 0).toLocaleString()} رکورد)`
                        : `Human-Readable OFAC Iran Viewer (${(data.ofac_summary?.iran_related_count ?? 0).toLocaleString()})`}
                    </button>
                    <button
                      type="button"
                      onClick={() => setConverterTab('csv')}
                      className={`px-3.5 py-1.5 text-xs font-bold rounded-md transition-colors cursor-pointer ${
                        converterTab === 'csv'
                          ? 'bg-emerald-700 text-white shadow-2xs'
                          : 'bg-white text-slate-700 border border-slate-300 hover:bg-emerald-50'
                      }`}
                    >
                      {lang === 'fa'
                        ? `مبدل فایل‌های CSV به اکسل (${(data.csv_datasets || []).length} جدول)`
                        : `Uploaded CSV-to-Excel Converter (${(data.csv_datasets || []).length} Tables)`}
                    </button>
                  </div>

                  {converterTab === 'ofac_iran' && (
                    <div className="flex items-center gap-2">
                      <input
                        type="text"
                        value={ofacViewerQuery}
                        onChange={(e) => setOfacViewerQuery(e.target.value)}
                        placeholder={
                          lang === 'fa'
                            ? 'فیلتر سریع در پیش‌نمایش اوفک ایران...'
                            : 'Filter preview by name, alias, or program...'
                        }
                        className="px-3 py-1.5 text-xs bg-white border border-slate-300 rounded-md w-64 focus:outline-none focus:ring-2 focus:ring-rose-500"
                      />
                      <button
                        type="button"
                        onClick={() => {
                          setActiveNav('search');
                          setFilterType('OFAC_SANCTION');
                          setSearchQuery(ofacViewerQuery || 'IRAN');
                          runUniversalSearchWithQuery(ofacViewerQuery || 'IRAN', {
                            type: 'OFAC_SANCTION',
                          });
                        }}
                        className="px-3 py-1.5 text-xs font-bold text-indigo-800 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 rounded-md cursor-pointer"
                      >
                        {lang === 'fa'
                          ? `جستجو در کل ${(data.ofac_summary?.total_entities ?? 0).toLocaleString()} رکورد ←`
                          : `Search All ${(data.ofac_summary?.total_entities ?? 0).toLocaleString()} →`}
                      </button>
                    </div>
                  )}
                </div>

                {converterTab === 'ofac_iran' ? (
                  (() => {
                    const sampleRows = (data.ofac_summary?.sample_iran_entities || []).filter((r) => {
                      const needle = ofacViewerQuery.trim().toLowerCase();
                      if (!needle) return true;
                      const hay = `${r.sdn_name || ''} ${r.programs || ''} ${r.aliases_text || ''} ${r.countries_text || ''} ${r.remarks || ''}`.toLowerCase();
                      return hay.includes(needle);
                    });

                    return (
                      <div className="divide-y divide-slate-200">
                        <div className="px-5 py-2.5 bg-rose-50/50 text-xs text-rose-950 flex flex-wrap items-center justify-between gap-2">
                          <span>
                            {lang === 'fa'
                              ? `پیش‌نمایش خوانای جدیدترین رکوردهای تحریمی مرتبط با ایران (برای دریافت کامل هر ${(data.ofac_summary?.iran_related_count ?? 0).toLocaleString()} رکورد، روی دکمه دانلود اکسل بالا کلیک کنید).`
                              : `Clean human-readable preview of recent Iran-linked OFAC designations (click "Download OFAC Iran Excel (.xlsx)" above for all ${(data.ofac_summary?.iran_related_count ?? 0).toLocaleString()} records).`}
                          </span>
                          <span className="font-mono-tabular font-semibold text-rose-800">
                            Pub #{data.ofac_summary?.last_publication_id || '—'}
                          </span>
                        </div>
                        <div className="overflow-x-auto max-h-[520px]">
                          <table className="w-full text-xs text-start border-collapse">
                            <thead>
                              <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 sticky top-0">
                                <th className="py-2.5 px-4 text-start font-bold">OFAC ID</th>
                                <th className="py-2.5 px-4 text-start font-bold">
                                  {lang === 'fa' ? 'نام و نوع' : 'Primary Name & Type'}
                                </th>
                                <th className="py-2.5 px-4 text-start font-bold">
                                  {lang === 'fa' ? 'برنامه‌های تحریمی' : 'Sanctions Programs'}
                                </th>
                                <th className="py-2.5 px-4 text-start font-bold">
                                  {lang === 'fa' ? 'اسامی مستعار (AKA) و کشورها' : 'Aliases (AKA) & Countries'}
                                </th>
                                <th className="py-2.5 px-4 text-start font-bold">
                                  {lang === 'fa' ? 'توضیحات رسمی' : 'Remarks'}
                                </th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-200">
                              {sampleRows.map((r, i) => {
                                const progs = String(r.programs || '')
                                  .replace(/\]\s*\[/g, '; ')
                                  .split(';')
                                  .map((p) => p.trim())
                                  .filter(Boolean);
                                return (
                                  <tr
                                    key={`${String(r.ent_num)}-${i}`}
                                    className="hover:bg-rose-50/40 even:bg-slate-50/40 transition-colors"
                                  >
                                    <td className="py-3 px-4 font-mono-tabular whitespace-nowrap">
                                      <div className="font-bold text-rose-800">
                                        #{String(r.ent_num)}
                                      </div>
                                      <span className="inline-block mt-1 px-1.5 py-0.5 text-[10px] font-bold rounded bg-rose-100 text-rose-900">
                                        {String(r.list_source || 'SDN')}
                                      </span>
                                    </td>
                                    <td className="py-3 px-4 min-w-[200px]">
                                      <div className="font-bold text-slate-900 text-xs">
                                        {String(r.sdn_name || '')}
                                      </div>
                                      <span className="inline-block mt-1 px-1.5 py-0.5 text-[10px] font-semibold uppercase bg-slate-200 text-slate-700 rounded">
                                        {String(r.sdn_type || 'entity')}
                                      </span>
                                    </td>
                                    <td className="py-3 px-4 min-w-[160px]">
                                      <div className="flex flex-wrap gap-1">
                                        {progs.map((p) => (
                                          <span
                                            key={p}
                                            className="px-1.5 py-0.5 text-[10px] font-mono-tabular font-bold bg-rose-100 text-rose-900 border border-rose-200 rounded"
                                          >
                                            {p}
                                          </span>
                                        ))}
                                      </div>
                                    </td>
                                    <td className="py-3 px-4 max-w-xs space-y-1 text-slate-700">
                                      {r.countries_text ? (
                                        <div className="font-semibold text-slate-900">
                                          {String(r.countries_text)}
                                        </div>
                                      ) : null}
                                      {r.aliases_text ? (
                                        <div className="text-[11px] text-slate-600 line-clamp-2">
                                          {String(r.aliases_text)}
                                        </div>
                                      ) : (
                                        <span className="text-slate-400">—</span>
                                      )}
                                    </td>
                                    <td className="py-3 px-4 max-w-sm text-[11px] text-slate-600 leading-relaxed">
                                      {String(r.remarks || '—').slice(0, 220)}
                                    </td>
                                  </tr>
                                );
                              })}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    );
                  })()
                ) : (
                  <>
                    {/* Dataset Selector, Instant Search & Preview All Controls */}
                    <div className="p-4 sm:p-5 bg-emerald-50/60 border-b border-emerald-200 space-y-4">
                      <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-3">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-xs font-semibold text-emerald-950">
                            {lang === 'fa' ? 'جدول فعال:' : 'Active CSV Table:'}
                          </span>
                          {(data.csv_datasets || []).map((ds) => (
                            <button
                              key={ds.id}
                              onClick={() =>
                                handleCsvFilterChange(ds.id, csvFilterQuery, csvPreviewAll, false)
                              }
                              className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors cursor-pointer ${
                                !csvCrossDatasetAudit && currentCsvDataset?.id === ds.id
                                  ? 'bg-emerald-700 text-white'
                                  : 'bg-white text-emerald-900 border border-emerald-300 hover:bg-emerald-100'
                              }`}
                            >
                              {ds.dataset_name} ({ds.row_count})
                            </button>
                          ))}
                          <button
                            onClick={() =>
                              handleCsvFilterChange(
                                selectedCsvId,
                                csvFilterQuery,
                                true,
                                !csvCrossDatasetAudit
                              )
                            }
                            className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors inline-flex items-center gap-1.5 cursor-pointer ${
                              csvCrossDatasetAudit
                                ? 'bg-indigo-700 text-white'
                                : 'bg-white text-indigo-900 border border-indigo-300 hover:bg-indigo-50'
                            }`}
                          >
                            <Layers className="w-3.5 h-3.5" />
                            <span>{t.csvCrossDatasetBtn}</span>
                          </button>
                        </div>

                        <div className="flex flex-wrap items-center gap-2">
                          <div className="relative flex-1 min-w-[220px]">
                            <input
                              type="text"
                              value={csvFilterQuery}
                              onChange={(e) =>
                                handleCsvFilterChange(
                                  currentCsvDataset?.id ?? selectedCsvId,
                                  e.target.value,
                                  csvPreviewAll,
                                  csvCrossDatasetAudit
                                )
                              }
                              placeholder={t.csvSearchPlaceholder}
                              className="w-full px-3 py-1.5 text-xs bg-white border border-emerald-300 rounded-md focus:outline-none focus:ring-2 focus:ring-emerald-600"
                            />
                          </div>

                          <button
                            type="button"
                            onClick={() =>
                              handleCsvFilterChange(
                                currentCsvDataset?.id ?? selectedCsvId,
                                csvFilterQuery,
                                !csvPreviewAll,
                                csvCrossDatasetAudit
                              )
                            }
                            className={`px-3.5 py-1.5 text-xs font-bold rounded-md transition-colors inline-flex items-center gap-1.5 cursor-pointer ${
                              csvPreviewAll
                                ? 'bg-amber-600 text-white hover:bg-amber-700'
                                : 'bg-emerald-800 text-white hover:bg-emerald-900'
                            }`}
                          >
                            <Eye className="w-3.5 h-3.5" />
                            <span>
                              {csvPreviewAll ? t.csvPreviewSubsetBtn : t.csvPreviewAllBtn}
                            </span>
                          </button>
                        </div>
                      </div>

                      <div className="flex flex-wrap items-center justify-between gap-2 px-3.5 py-2 bg-white border border-emerald-200 rounded-md text-xs">
                        <div className="font-semibold text-slate-800">
                          {lang === 'fa' ? (
                            <span>
                              نمایش{' '}
                              <span className="font-mono-tabular text-emerald-800">
                                {displayedCsvCount}
                              </span>{' '}
                              رکورد از مجموع{' '}
                              <span className="font-mono-tabular text-emerald-800">
                                {totalCsvMatching}
                              </span>{' '}
                              رکورد منطبق
                            </span>
                          ) : (
                            <span>
                              Showing{' '}
                              <span className="font-mono-tabular text-emerald-800">
                                {displayedCsvCount}
                              </span>{' '}
                              of{' '}
                              <span className="font-mono-tabular text-emerald-800">
                                {totalCsvMatching}
                              </span>{' '}
                              matching records
                            </span>
                          )}
                        </div>

                        {isCsvSubset && !csvPreviewAll && (
                          <button
                            type="button"
                            onClick={() =>
                              handleCsvFilterChange(
                                currentCsvDataset?.id ?? selectedCsvId,
                                csvFilterQuery,
                                true,
                                csvCrossDatasetAudit
                              )
                            }
                            className="text-xs font-bold text-indigo-700 hover:text-indigo-950 underline inline-flex items-center gap-1 cursor-pointer"
                          >
                            <Eye className="w-3.5 h-3.5" />
                            <span>
                              {lang === 'fa'
                                ? `مشاهده هر ${totalCsvMatching} رکورد منطبق ←`
                                : `Preview all ${totalCsvMatching} matching records →`}
                            </span>
                          </button>
                        )}
                      </div>
                    </div>

                    {currentCsvDataset ? (
                      <div
                        className={`overflow-x-auto ${csvPreviewAll ? 'max-h-[640px]' : 'max-h-96'}`}
                      >
                        <table className="w-full text-xs text-start border-collapse">
                          <thead>
                            <tr className="bg-slate-100 border-b border-slate-300 text-slate-700 sticky top-0">
                              <th className="py-2.5 px-3 border-e border-slate-300 font-mono-tabular text-center w-12 bg-slate-200">
                                #
                              </th>
                              {currentCsvDataset.headers.map((h) => (
                                <th
                                  key={h}
                                  className="py-2.5 px-4 border-e border-slate-200 font-bold text-slate-800 whitespace-nowrap"
                                >
                                  {h}
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-200">
                            {currentCsvRows.map((r) => (
                              <tr
                                key={`${r.id}-${r.row_number}`}
                                className="hover:bg-emerald-50/60 transition-colors even:bg-slate-50/60"
                              >
                                <td className="py-2.5 px-3 border-e border-slate-200 font-mono-tabular text-center text-slate-500 bg-slate-100/70 font-semibold">
                                  {r.row_number}
                                </td>
                                {currentCsvDataset.headers.map((h) => (
                                  <td
                                    key={h}
                                    className={`py-2.5 px-4 border-e border-slate-100 text-slate-800 ${
                                      csvPreviewAll ? 'min-w-[160px]' : 'max-w-xs truncate'
                                    }`}
                                    title={r.cells[h] || ''}
                                  >
                                    {r.cells[h] || ''}
                                  </td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : null}
                  </>
                )}
              </section>

              {/* Standard Archive Export Cards (.xlsx, .csv, .json) */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-white border border-emerald-200 border-t-4 border-t-emerald-600 rounded-lg p-6 flex flex-col justify-between space-y-4">
                  <div className="space-y-2">
                    <div className="text-base font-bold text-emerald-950">{t.exportExcelTitle}</div>
                    <p className="text-xs text-slate-600 leading-relaxed">{t.exportExcelDesc}</p>
                  </div>
                  <a
                    href="/api/export/xlsx"
                    className="w-full py-2.5 px-4 text-xs font-semibold text-center text-white bg-emerald-700 rounded-md hover:bg-emerald-800 transition-colors"
                  >
                    {t.downloadBtn} (.xlsx)
                  </a>
                </div>

                <div className="bg-white border border-sky-200 border-t-4 border-t-sky-600 rounded-lg p-6 flex flex-col justify-between space-y-4">
                  <div className="space-y-2">
                    <div className="text-base font-bold text-sky-950">{t.exportCsvTitle}</div>
                    <p className="text-xs text-slate-600 leading-relaxed">{t.exportCsvDesc}</p>
                  </div>
                  <a
                    href="/api/export/csv"
                    className="w-full py-2.5 px-4 text-xs font-semibold text-center text-white bg-sky-700 rounded-md hover:bg-sky-800 transition-colors"
                  >
                    {t.downloadBtn} (.csv)
                  </a>
                </div>

                <div className="bg-white border border-indigo-200 border-t-4 border-t-indigo-600 rounded-lg p-6 flex flex-col justify-between space-y-4">
                  <div className="space-y-2">
                    <div className="text-base font-bold text-indigo-950">{t.exportJsonTitle}</div>
                    <p className="text-xs text-slate-600 leading-relaxed">{t.exportJsonDesc}</p>
                  </div>
                  <a
                    href="/api/export/json"
                    className="w-full py-2.5 px-4 text-xs font-semibold text-center text-white bg-indigo-700 rounded-md hover:bg-indigo-800 transition-colors"
                  >
                    {t.downloadBtn} (.json)
                  </a>
                </div>
              </div>

              {/* Backup & Restore Section */}
              <div className="bg-white border border-purple-200 rounded-lg p-4 sm:p-6 space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-4">
                  <div>
                    <h3 className="text-base font-bold text-purple-950">{t.backupTitle}</h3>
                    <p className="text-xs text-slate-500">
                      Directory: <span className="font-mono-tabular">{data.paths.backups_dir}</span>
                    </p>
                  </div>
                  <button
                    onClick={handleCreateBackup}
                    disabled={busyAction === 'backup'}
                    className="px-4 py-2 text-xs font-semibold text-white bg-purple-700 rounded-md hover:bg-purple-800 transition-colors cursor-pointer"
                  >
                    {t.actionCreateBackup}
                  </button>
                </div>

                {confirmRestorePath && (
                  <div className="p-4 bg-amber-50 border border-amber-300 rounded-md space-y-3">
                    <div className="text-sm font-medium text-amber-950">
                      {t.confirmRestorePrompt}
                    </div>
                    <div className="text-xs font-mono-tabular text-amber-800 break-all">
                      {confirmRestorePath}
                    </div>
                    <div className="flex items-center gap-3">
                      <button
                        onClick={() => handleConfirmRestore(confirmRestorePath)}
                        className="px-3 py-1.5 text-xs font-semibold text-white bg-amber-800 rounded hover:bg-amber-900 cursor-pointer"
                      >
                        {t.confirmYes}
                      </button>
                      <button
                        onClick={() => setConfirmRestorePath(null)}
                        className="px-3 py-1.5 text-xs font-medium text-slate-700 bg-white border border-slate-300 rounded cursor-pointer"
                      >
                        {t.confirmCancel}
                      </button>
                    </div>
                  </div>
                )}

                <div className="overflow-x-auto">
                  <table className="w-full text-sm text-start border-collapse">
                    <thead>
                      <tr className="border-b border-slate-200 text-xs text-slate-500">
                        <th className="py-2.5 px-4 text-start font-medium">Backup Filename</th>
                        <th className="py-2.5 px-4 text-start font-medium">Created UTC</th>
                        <th className="py-2.5 px-4 text-end font-medium">Size</th>
                        <th className="py-2.5 px-4 text-start font-medium">Integrity</th>
                        <th className="py-2.5 px-4 text-end font-medium">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200">
                      {data.backups.map((b) => (
                        <tr key={b.path}>
                          <td className="py-3 px-4 font-mono-tabular text-xs">{b.filename}</td>
                          <td className="py-3 px-4 font-mono-tabular text-xs text-slate-600">
                            {b.created_at}
                          </td>
                          <td className="py-3 px-4 font-mono-tabular text-xs text-end">
                            {(b.size_bytes / 1024).toFixed(1)} KB
                          </td>
                          <td className="py-3 px-4 text-xs text-emerald-700 font-medium">
                            {b.integrity_verified ? 'PRAGMA ok' : 'Failed'}
                          </td>
                          <td className="py-3 px-4 text-end">
                            <button
                              onClick={() => setConfirmRestorePath(b.path)}
                              className="text-xs font-semibold text-purple-800 hover:underline cursor-pointer"
                            >
                              {t.restoreBtn}
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* 8. COLLECTION HISTORY & RECOVERY */}
          {activeNav === 'history' && (
            <div className="space-y-6">
              <div className="bg-white border border-orange-200 rounded-lg p-4 sm:p-6 space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-4">
                  <div>
                    <h3 className="text-base font-bold text-slate-900">
                      Collection Jobs & Interrupted-Task Recovery
                    </h3>
                    <p className="text-xs text-slate-500">
                      Checkpoints are persisted in collection_jobs.checkpoint_data after every page.
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2.5">
                    {(busyAction === 'update' || busyAction === 'pipeline') && (
                      <button
                        type="button"
                        onClick={handleStopCrawl}
                        className="px-4 py-2 text-xs font-bold text-white bg-red-600 hover:bg-red-700 rounded-md inline-flex items-center gap-1.5 cursor-pointer shadow-xs"
                      >
                        <Square className="w-3.5 h-3.5 fill-current" />
                        <span>{lang === 'fa' ? 'توقف خزش (Stop)' : 'Stop Crawling'}</span>
                      </button>
                    )}
                    <button
                      onClick={() => handleUpdateArchive(1)}
                      disabled={busyAction !== null}
                      className="px-3.5 py-2 text-xs font-semibold text-amber-900 bg-amber-100 border border-amber-300 rounded-md hover:bg-amber-200 cursor-pointer disabled:opacity-50"
                    >
                      {t.simulateInterruptBtn}
                    </button>
                    <button
                      onClick={() => handleUpdateArchive(undefined, 12, true)}
                      disabled={busyAction !== null}
                      className="px-4 py-2 text-xs font-semibold text-white bg-sky-700 rounded-md hover:bg-sky-800 cursor-pointer disabled:opacity-50"
                    >
                      {t.actionUpdateArchive}
                    </button>
                    <button
                      onClick={() => handleUpdateArchive(undefined, 0, true)}
                      disabled={busyAction !== null}
                      className="px-4 py-2 text-xs font-bold text-indigo-950 bg-indigo-100 border border-indigo-300 rounded-md hover:bg-indigo-200 cursor-pointer disabled:opacity-50"
                    >
                      {lang === 'fa'
                        ? 'خزش عنکبوتی کامل (تمام صفحات)'
                        : 'Spider All Pages to End'}
                    </button>
                  </div>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-sm text-start border-collapse">
                    <thead>
                      <tr className="border-b border-slate-200 text-xs text-slate-500">
                        <th className="py-2.5 px-4 text-start font-medium">Job ID</th>
                        <th className="py-2.5 px-4 text-start font-medium">Type</th>
                        <th className="py-2.5 px-4 text-start font-medium">Status</th>
                        <th className="py-2.5 px-4 text-end font-medium">Processed</th>
                        <th className="py-2.5 px-4 text-start font-medium">Started UTC</th>
                        <th className="py-2.5 px-4 text-end font-medium">Recovery</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200">
                      {data.jobs.map((job) => (
                        <tr key={job.id}>
                          <td className="py-3 px-4 font-mono-tabular text-xs">#{job.id}</td>
                          <td className="py-3 px-4 font-mono-tabular text-xs">{job.job_type}</td>
                          <td className="py-3 px-4 text-xs font-semibold">
                            <span
                              className={
                                job.status === 'COMPLETED'
                                  ? 'text-emerald-700'
                                  : job.status === 'INTERRUPTED'
                                  ? 'text-amber-700'
                                  : 'text-slate-700'
                              }
                            >
                              {job.status}
                            </span>
                          </td>
                          <td className="py-3 px-4 font-mono-tabular text-xs text-end">
                            {job.processed_count} / {job.total_discovered}
                          </td>
                          <td className="py-3 px-4 font-mono-tabular text-xs text-slate-500">
                            {job.started_at}
                          </td>
                          <td className="py-3 px-4 text-end">
                            {job.status === 'INTERRUPTED' && (
                              <button
                                onClick={() => handleResumeJob(job.id)}
                                className="px-3 py-1 text-xs font-semibold text-white bg-amber-700 rounded hover:bg-amber-800 cursor-pointer"
                              >
                                {t.resumeJobBtn}
                              </button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Granular Per-URL Audit History */}
              <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
                <div className="px-4 sm:px-6 py-3 bg-slate-50 border-b border-slate-200 text-xs font-semibold text-slate-700">
                  Per-URL Collection Audit Log (collection_history)
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs text-start border-collapse">
                    <thead>
                      <tr className="border-b border-slate-200 text-slate-500">
                        <th className="py-2.5 px-4 sm:px-6 text-start font-medium">Target URL</th>
                        <th className="py-2.5 px-4 text-start font-medium">Type</th>
                        <th className="py-2.5 px-4 text-start font-medium">Action</th>
                        <th className="py-2.5 px-4 sm:px-6 text-start font-medium">Audit Note</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200">
                      {data.history.slice(0, 20).map((h) => (
                        <tr key={h.id}>
                          <td className="py-2.5 px-4 sm:px-6 font-mono-tabular text-slate-800 break-all">
                            {h.target_url}
                          </td>
                          <td className="py-2.5 px-4 font-mono-tabular">{h.record_type}</td>
                          <td
                            className={`py-2.5 px-4 font-mono-tabular font-semibold ${
                              h.action_taken === 'EXCLUDED_POLICY'
                                ? 'text-amber-700'
                                : 'text-emerald-700'
                            }`}
                          >
                            {h.action_taken}
                          </td>
                          <td className="py-2.5 px-4 sm:px-6 text-slate-600">{h.message}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* 9. SETTINGS, FULL PORTABLE TEAM BACKUP, WINDOWS INSTALLER (.EXE), STORAGE PATH & SCHEDULER */}
          {activeNav === 'settings' && (
            <div className="space-y-6">
              {/* REAL FULL PORTABLE BACKUP & RESTORE FOR ALL 5 TEAM PCS */}
              <section className="bg-white border-2 border-emerald-400 rounded-xl overflow-hidden shadow-md">
                <div className="bg-emerald-950 text-white px-5 sm:px-6 py-4 flex flex-wrap items-center justify-between gap-4 border-b border-emerald-800">
                  <div className="space-y-1">
                    <div className="text-xs font-bold text-emerald-300 uppercase tracking-wider">
                      {lang === 'fa'
                        ? 'بکاپ کامل و قابل انتقال برای هر ۵ کامپیوتر تیم (بدون نیاز به دانلود مجدد)'
                        : 'FULL PORTABLE TEAM BACKUP & RESTORE (SHARE ACROSS ALL 5 PCS — ZERO RE-DOWNLOAD)'}
                    </div>
                    <h3 className="text-base sm:text-lg font-bold text-white">
                      {lang === 'fa'
                        ? 'پشتیبان‌گیری کامل از کل برنامه و داده‌ها (.ZIP) و بازیابی روی سیستم‌های دیگر'
                        : 'Full Archive Backup Package (.ZIP) — Everything Offline in One File'}
                    </h3>
                    <p className="text-xs text-emerald-100/90 max-w-3xl">
                      {lang === 'fa'
                        ? 'این بکاپ شامل تمام دیتابیس SQLite + ایندکس جستجو (کل ویکی‌ایران + ۲۰٬۰۸۵ رکورد OFAC + کل OpenSanctions + جداول CSV + تنظیمات) به‌علاوه فایل‌های خام CSV و کد امنیتی SHA-256 است. کافیست روی ۱ سیستم دانلود کنید و این فایل .ZIP را روی ۴ سیستم دیگر بازیابی کنید.'
                        : 'Packages the entire consistent SQLite database + FTS5 search index (all WikIran articles/leaks + all OFAC SDN/Consolidated + all OpenSanctions global targets + CSV workbench + crawl frontier + settings) plus raw OFAC/OpenSanctions CSVs and SHA-256 manifest into one portable .ZIP.'}
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2.5 shrink-0">
                    <button
                      type="button"
                      disabled={chunkDownloadProgress !== null}
                      onClick={() =>
                        downloadChunkedZip(
                          '/api/backup/full-prepare',
                          '/api/backup/full-chunk',
                          {},
                          lang === 'fa' ? 'دانلود بکاپ کامل' : 'Full Backup Download'
                        )
                      }
                      className="px-5 py-2.5 text-xs sm:text-sm font-bold text-emerald-950 bg-emerald-300 hover:bg-emerald-200 disabled:opacity-60 rounded-lg transition-colors inline-flex items-center gap-2 shadow-xs cursor-pointer"
                    >
                      <HardDriveDownload className="w-4 h-4 shrink-0" />
                      <span>
                        {lang === 'fa'
                          ? 'دانلود بکاپ کامل همه داده‌ها (.ZIP)'
                          : 'Download Full Backup (.ZIP)'}
                      </span>
                    </button>
                    <label className="px-4 py-2.5 text-xs sm:text-sm font-bold text-white bg-indigo-600 hover:bg-indigo-500 border border-indigo-400 rounded-lg transition-colors inline-flex items-center gap-2 cursor-pointer shadow-xs">
                      <Upload className="w-4 h-4 shrink-0" />
                      <span>
                        {busyAction === 'full_restore'
                          ? lang === 'fa'
                            ? 'در حال بازیابی بکاپ...'
                            : 'Restoring Full Backup...'
                          : lang === 'fa'
                          ? 'بازیابی فایل بکاپ (.ZIP) روی این سیستم'
                          : 'Restore Full Backup (.ZIP)'}
                      </span>
                      <input
                        type="file"
                        accept=".zip,.db"
                        onChange={handleFullBackupRestoreUpload}
                        disabled={busyAction !== null}
                        className="hidden"
                      />
                    </label>
                  </div>
                </div>

                <div className="p-5 sm:p-6 bg-emerald-50/35 space-y-4">
                  {fullBackupMsg && (
                    <div className="px-4 py-2.5 rounded-lg bg-emerald-100 border border-emerald-300 text-xs font-semibold text-emerald-950 flex items-center justify-between gap-2">
                      <span>{fullBackupMsg}</span>
                      <button
                        type="button"
                        onClick={() => setFullBackupMsg(null)}
                        className="text-emerald-800 hover:text-emerald-950 cursor-pointer"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  )}

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                    <div className="bg-white border border-emerald-200 rounded-lg p-3">
                      <div className="text-slate-500">
                        {lang === 'fa' ? 'آرشیو ویکی‌ایران' : 'WikIran Records'}
                      </div>
                      <div className="text-lg font-bold font-mono-tabular text-slate-900 mt-0.5">
                        {(data.stats.articles_count + data.stats.publications_count).toLocaleString()}
                      </div>
                    </div>
                    <div className="bg-white border border-emerald-200 rounded-lg p-3">
                      <div className="text-slate-500">
                        {lang === 'fa' ? 'تحریم‌های اوفک' : 'OFAC Entities'}
                      </div>
                      <div className="text-lg font-bold font-mono-tabular text-rose-700 mt-0.5">
                        {(data.ofac_summary?.total_entities ?? 0).toLocaleString()}
                      </div>
                    </div>
                    <div className="bg-white border border-emerald-200 rounded-lg p-3">
                      <div className="text-slate-500">
                        {lang === 'fa' ? 'تحریم‌های OpenSanctions' : 'OpenSanctions Targets'}
                      </div>
                      <div className="text-lg font-bold font-mono-tabular text-amber-700 mt-0.5">
                        {(data.opensanctions_summary?.total_entities ?? 0).toLocaleString()}
                      </div>
                    </div>
                    <div className="bg-white border border-emerald-200 rounded-lg p-3">
                      <div className="text-slate-500">
                        {lang === 'fa' ? 'حجم فعلی دیتابیس' : 'Current DB Size'}
                      </div>
                      <div className="text-lg font-bold font-mono-tabular text-emerald-700 mt-0.5">
                        {data.storage_volume?.db_size_label || '—'}
                      </div>
                    </div>
                  </div>

                  {data.backups && data.backups.length > 0 && (
                    <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
                      <div className="px-4 py-2.5 bg-slate-50 border-b border-slate-200 flex items-center justify-between text-xs font-bold text-slate-700">
                        <span>
                          {lang === 'fa'
                            ? `بکاپ‌های ذخیره‌شده روی این سیستم (${data.backups.length})`
                            : `Saved Local Backups (${data.backups.length})`}
                        </span>
                        <span className="font-mono-tabular text-[11px] text-slate-500">
                          {data.paths.backups_dir}
                        </span>
                      </div>
                      <div className="divide-y divide-slate-100 max-h-48 overflow-y-auto">
                        {data.backups.slice(0, 6).map((b) => (
                          <div
                            key={b.path}
                            className="px-4 py-2.5 flex flex-wrap items-center justify-between gap-2 text-xs"
                          >
                            <div className="min-w-0">
                              <div className="font-mono-tabular font-semibold text-slate-900 truncate">
                                {b.filename}
                              </div>
                              <div className="text-[11px] text-slate-500 font-mono-tabular">
                                {(b.size_bytes / (1024 * 1024)).toFixed(2)} MB · {b.created_at}
                              </div>
                            </div>
                            <div className="flex items-center gap-2 shrink-0">
                              {b.filename.endsWith('.zip') && (
                                <button
                                  type="button"
                                  disabled={chunkDownloadProgress !== null}
                                  onClick={() =>
                                    downloadChunkedZip(
                                      '/api/backup/full-prepare',
                                      '/api/backup/full-chunk',
                                      { path: b.path },
                                      b.filename
                                    )
                                  }
                                  className="px-2.5 py-1 text-[11px] font-bold text-emerald-900 bg-emerald-50 hover:bg-emerald-100 border border-emerald-300 rounded cursor-pointer"
                                >
                                  {lang === 'fa' ? 'دانلود ZIP' : 'Download ZIP'}
                                </button>
                              )}
                              <button
                                type="button"
                                onClick={() => handleConfirmRestore(b.path)}
                                disabled={busyAction !== null}
                                className="px-2.5 py-1 text-[11px] font-bold text-indigo-800 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 rounded cursor-pointer"
                              >
                                {lang === 'fa' ? 'بازیابی' : 'Restore'}
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </section>

              {/* WINDOWS PORTABLE EDITION (.ZIP — ZERO .EXE) & USER-CONFIGURABLE STORAGE PATH */}
              <section className="bg-white border-2 border-emerald-400 rounded-xl overflow-hidden shadow-xs">
                <div className="bg-slate-900 text-white px-5 sm:px-6 py-4 flex flex-wrap items-center justify-between gap-4 border-b border-slate-800">
                  <div className="space-y-1">
                    <div className="text-xs font-bold text-emerald-400 uppercase tracking-wider">
                      {lang === 'fa'
                        ? 'نسخه پرتابل ویندوز (.ZIP) — بدون فایل .EXE، بدون هشدار امنیتی ویندوز، بدون نیاز به نصب'
                        : 'WINDOWS PORTABLE EDITION (.ZIP) — ZERO .EXE FILES, NO WINDOWS SECURITY BLOCK, NO INSTALLATION'}
                    </div>
                    <h3 className="text-base sm:text-lg font-bold text-white">
                      {lang === 'fa'
                        ? 'دانلود نسخه کامل و پرتابل ویندوز (WikIranArchive_Portable_Windows.zip)'
                        : 'WikIran Archive Portable Edition (WikIranArchive_Portable_Windows.zip)'}
                    </h3>
                    <p className="text-xs text-slate-300 max-w-3xl">
                      {lang === 'fa'
                        ? 'بسته کامل و آماده اجرای ویندوز شامل کل برنامه، رابط کاربری، موتور پایتون، تمام ۹۷٬۳۰۰+ رکورد آفلاین (OFAC + OpenSanctions + WikIran) و تنها چند فایل ساده .bat — بدون هیچ فایل .exe و بدون هیچ هشدار Windows Defender یا SmartScreen. کافی است از حالت فشرده خارج کنید و اجرا نمایید!'
                        : 'Self-contained portable bundle with the full app, compiled UI, Python engine, all offline OFAC + OpenSanctions + WikIran records, and simple .bat launchers — zero .exe files, zero Windows Defender/SmartScreen warnings, and no installation wizard. Just unzip anywhere and run!'}
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2 shrink-0">
                    <button
                      type="button"
                      disabled={chunkDownloadProgress !== null}
                      onClick={() =>
                        downloadChunkedZip(
                          '/api/download/windows-portable-prepare',
                          '/api/download/windows-portable-chunk',
                          {},
                          lang === 'fa'
                            ? 'دانلود نسخه کامل پرتابل (با دیتابیس)'
                            : 'Full Portable Edition (With DB)'
                        )
                      }
                      className="px-4 py-2.5 text-xs sm:text-sm font-bold text-white bg-emerald-600 hover:bg-emerald-500 disabled:opacity-60 rounded-lg transition-colors inline-flex items-center gap-2 shadow-xs cursor-pointer"
                    >
                      <HardDriveDownload className="w-4 h-4 shrink-0" />
                      <span>
                        {lang === 'fa'
                          ? 'دانلود نسخه کامل با دیتابیس (~72 MB)'
                          : 'Download Full Portable (~72 MB, Pre-Loaded DB)'}
                      </span>
                    </button>
                    <a
                      href="/api/download/windows-portable-lite-zip"
                      download="WikIranArchive_Portable_Windows_Release.zip"
                      className="px-4 py-2.5 text-xs sm:text-sm font-bold text-slate-900 bg-sky-300 hover:bg-sky-200 rounded-lg transition-colors inline-flex items-center gap-2 shadow-xs"
                    >
                      <Download className="w-4 h-4 shrink-0" />
                      <span>
                        {lang === 'fa'
                          ? 'دانلود سریع نسخه ویندوز (~1 MB)'
                          : 'Fast Windows Release (~1 MB Direct Link)'}
                      </span>
                    </a>
                  </div>
                </div>

                {chunkDownloadProgress && (
                  <div className="px-5 sm:px-6 py-3.5 bg-emerald-950 text-emerald-100 border-b border-emerald-800 space-y-2">
                    <div className="flex items-center justify-between gap-2 text-xs font-bold">
                      <span className="inline-flex items-center gap-2">
                        <RefreshCw className="w-3.5 h-3.5 animate-spin text-emerald-400" />
                        <span>{chunkDownloadProgress.label}</span>
                      </span>
                      <span className="font-mono-tabular text-emerald-300">
                        {chunkDownloadProgress.loadedMb} / {chunkDownloadProgress.totalMb} MB ({chunkDownloadProgress.percent}%)
                      </span>
                    </div>
                    <div className="w-full h-2 bg-emerald-900 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-emerald-400 rounded-full transition-all duration-200"
                        style={{ width: `${chunkDownloadProgress.percent}%` }}
                      />
                    </div>
                  </div>
                )}

                <div className="p-5 sm:p-6 grid grid-cols-1 lg:grid-cols-2 gap-6 bg-slate-50/60">
                  {/* Left Column: User-Selectable Storage Path */}
                  <form
                    onSubmit={handleSaveStoragePath}
                    className="bg-white border border-slate-200 rounded-xl p-5 flex flex-col justify-between space-y-4"
                  >
                    <div className="space-y-3">
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-xs font-bold uppercase tracking-wider px-2.5 py-0.5 rounded bg-indigo-100 text-indigo-950">
                          {lang === 'fa' ? 'مسیر ذخیره‌سازی اطلاعات' : 'CUSTOM STORAGE PATH'}
                        </span>
                        <span className="text-xs font-mono-tabular text-emerald-700 font-semibold">
                          SQLite DB + Excel + Backups
                        </span>
                      </div>
                      <h4 className="text-sm sm:text-base font-bold text-slate-900">
                        {lang === 'fa'
                          ? 'انتخاب محل ذخیره دیتابیس، فایل‌های اکسل و نسخه‌های پشتیبان'
                          : 'Choose Where to Store Archive Data, Excel Reports & Backups'}
                      </h4>
                      <p className="text-xs text-slate-600 leading-relaxed">
                        {lang === 'fa'
                          ? 'در نسخه پرتابل (.zip) تمام اطلاعات به‌طور خودکار داخل پوشه data کنار برنامه ذخیره می‌شوند و می‌توانید کل پوشه را با فلش به هر ۵ کامپیوتر منتقل کنید. همچنین در اینجا می‌توانید مسیر دلخواه دیگری روی ویندوز تنظیم کنید.'
                          : 'In the Portable Edition (.zip), all data is stored self-contained inside the extracted folder’s own data/ directory so you can copy the entire folder via USB to all 5 office PCs. You can also set a custom storage path below.'}
                      </p>

                      <div className="space-y-2 pt-1">
                        <label className="block text-xs font-semibold text-slate-700">
                          {lang === 'fa' ? 'مسیر پوشه ذخیره‌سازی (Storage Path):' : 'Storage Folder Path:'}
                        </label>
                        <div className="flex flex-col sm:flex-row gap-2">
                          <input
                            type="text"
                            dir="ltr"
                            value={storagePathInput}
                            onChange={(e) => setStoragePathInput(e.target.value)}
                            placeholder="C:\WikIranArchive"
                            className="flex-1 px-3 py-2 text-xs font-mono-tabular border border-slate-300 rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-indigo-600"
                          />
                          <button
                            type="submit"
                            disabled={busyAction === 'save-storage-path'}
                            className="px-4 py-2 text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700 rounded-md transition-colors cursor-pointer whitespace-nowrap"
                          >
                            {lang === 'fa' ? 'ذخیره مسیر' : 'Save Storage Path'}
                          </button>
                        </div>

                        {/* Quick Path Presets */}
                        <div className="flex flex-wrap items-center gap-1.5 pt-1">
                          <span className="text-[11px] text-slate-500">
                            {lang === 'fa' ? 'مسیرهای پیشنهادی:' : 'Presets:'}
                          </span>
                          {[
                            'C:\\WikIranArchive',
                            'D:\\WikIranArchive',
                            'C:\\Users\\Public\\WikIranArchive',
                          ].map((preset) => (
                            <button
                              key={preset}
                              type="button"
                              onClick={() => setStoragePathInput(preset)}
                              className="px-2 py-0.5 text-[11px] font-mono-tabular bg-slate-100 hover:bg-indigo-50 text-slate-700 hover:text-indigo-800 border border-slate-300 rounded cursor-pointer"
                            >
                              {preset}
                            </button>
                          ))}
                        </div>
                      </div>
                    </div>

                    <div className="pt-3 border-t border-slate-100 space-y-1 text-xs text-slate-600 font-mono-tabular" dir="ltr">
                      <div>Active Base Folder: {data.paths.base_dir}</div>
                      <div>SQLite Database: {data.paths.db_path}</div>
                      <div>Excel Exports: {data.paths.exports_dir}</div>
                    </div>
                  </form>

                  {/* Right Column: Portable .ZIP Step-by-Step Guide & Bundled .BAT Files */}
                  <div className="bg-white border border-emerald-200 rounded-xl p-5 flex flex-col justify-between space-y-4">
                    <div className="space-y-3">
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-xs font-bold uppercase tracking-wider px-2.5 py-0.5 rounded bg-emerald-100 text-emerald-950">
                          {lang === 'fa'
                            ? 'بدون فایل .EXE • فقط فایل‌های .BAT شفاف'
                            : 'ZERO .EXE • CLEAN .BAT PORTABLE BUNDLE'}
                        </span>
                        <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
                      </div>
                      <h4 className="text-sm sm:text-base font-bold text-slate-900">
                        {lang === 'fa'
                          ? 'نحوه اجرا در ۳ گام ساده (مناسب برای هر ۵ کامپیوتر بدون دانلود مجدد)'
                          : 'How to Run in 3 Simple Steps (Copy Folder to All 5 PCs — Zero Re-Download)'}
                      </h4>
                      <ol className="list-decimal list-inside space-y-2 text-xs text-slate-700 leading-relaxed">
                        <li>
                          {lang === 'fa' ? (
                            <>
                              <strong className="text-slate-900">استخراج فایل ZIP:</strong> فایل{' '}
                              <code className="px-1 py-0.5 bg-slate-100 rounded font-mono-tabular">WikIranArchive_Portable_Windows.zip</code>{' '}
                              را در هر مسیری (مثلاً <code className="px-1 py-0.5 bg-slate-100 rounded font-mono-tabular">C:\WikIranArchive</code> یا فلش USB) از حالت فشرده خارج کنید. هیچ فایل <code className="font-mono-tabular">.exe</code> داخل آن نیست.
                            </>
                          ) : (
                            <>
                              <strong className="text-slate-900">Unzip Anywhere:</strong> Extract{' '}
                              <code className="px-1 py-0.5 bg-slate-100 rounded font-mono-tabular">WikIranArchive_Portable_Windows.zip</code>{' '}
                              to any folder (e.g. <code className="px-1 py-0.5 bg-slate-100 rounded font-mono-tabular">C:\WikIranArchive</code> or USB drive). Contains zero <code className="font-mono-tabular">.exe</code> files and needs no Node.js.
                            </>
                          )}
                        </li>
                        <li>
                          {lang === 'fa' ? (
                            <>
                              <strong className="text-slate-900">فقط بار اول — <code className="px-1 py-0.5 bg-emerald-50 text-emerald-900 rounded font-mono-tabular">1_Install_Prerequisites.bat</code>:</strong>{' '}
                              وجود Python 3.11+ را بررسی می‌کند (در صورت نبودن، نسخه رسمی و امضاشده پایتون را از طریق <code className="font-mono-tabular">winget</code> نصب می‌کند) و تنها کتابخانه سبک <code className="font-mono-tabular">openpyxl</code> را برای خروجی اکسل نصب می‌نماید.
                            </>
                          ) : (
                            <>
                              <strong className="text-slate-900">First Time Only — <code className="px-1 py-0.5 bg-emerald-50 text-emerald-900 rounded font-mono-tabular">1_Install_Prerequisites.bat</code>:</strong>{' '}
                              Checks for Python 3.11+ (auto-installs official signed Python via <code className="font-mono-tabular">winget</code> if missing) and installs the tiny <code className="font-mono-tabular">openpyxl</code> Excel helper.
                            </>
                          )}
                        </li>
                        <li>
                          {lang === 'fa' ? (
                            <>
                              <strong className="text-slate-900">اجرای روزانه — <code className="px-1 py-0.5 bg-emerald-50 text-emerald-900 rounded font-mono-tabular">2_Start_WikIran_Archive.bat</code>:</strong>{' '}
                              سرور محلی پایتون را با دیتابیس کامل داخل همین پوشه اجرا کرده و برنامه را در پنجره اختصاصی Edge باز می‌کند.
                            </>
                          ) : (
                            <>
                              <strong className="text-slate-900">Daily Launch — <code className="px-1 py-0.5 bg-emerald-50 text-emerald-900 rounded font-mono-tabular">2_Start_WikIran_Archive.bat</code>:</strong>{' '}
                              Starts the pure-Python local server using the pre-loaded offline database inside the folder and opens the app in a clean Edge desktop window.
                            </>
                          )}
                        </li>
                        <li>
                          {lang === 'fa' ? (
                            <>
                              <strong className="text-slate-900">ابزارهای اختیاری داخل بسته:</strong>{' '}
                              <code className="px-1 py-0.5 bg-slate-100 rounded font-mono-tabular">Create_Desktop_Shortcut.bat</code> (ساخت میانبر دسکتاپ) و{' '}
                              <code className="px-1 py-0.5 bg-slate-100 rounded font-mono-tabular">3_Stop_WikIran_Archive.bat</code> (توقف ایمن سرور).
                            </>
                          ) : (
                            <>
                              <strong className="text-slate-900">Included Helpers:</strong>{' '}
                              <code className="px-1 py-0.5 bg-slate-100 rounded font-mono-tabular">Create_Desktop_Shortcut.bat</code> (optional Desktop shortcut) &amp;{' '}
                              <code className="px-1 py-0.5 bg-slate-100 rounded font-mono-tabular">3_Stop_WikIran_Archive.bat</code> (graceful stop).
                            </>
                          )}
                        </li>
                      </ol>
                    </div>

                    <div className="pt-3 border-t border-slate-100 flex flex-wrap items-center gap-2.5">
                      <button
                        type="button"
                        disabled={chunkDownloadProgress !== null}
                        onClick={() =>
                          downloadChunkedZip(
                            '/api/download/windows-portable-prepare',
                            '/api/download/windows-portable-chunk',
                            {},
                            lang === 'fa'
                              ? 'دانلود نسخه کامل پرتابل (با دیتابیس)'
                              : 'Full Portable Edition (With DB)'
                          )
                        }
                        className="flex-1 py-2.5 px-4 text-xs sm:text-sm font-bold text-center text-white bg-emerald-700 hover:bg-emerald-800 disabled:opacity-60 rounded-lg transition-colors inline-flex items-center justify-center gap-2 shadow-xs cursor-pointer"
                      >
                        <HardDriveDownload className="w-4 h-4 shrink-0" />
                        <span>
                          {lang === 'fa'
                            ? 'دانلود نسخه کامل با دیتابیس (~72 MB)'
                            : 'Full Portable ZIP (~72 MB w/ DB)'}
                        </span>
                      </button>
                      <a
                        href="/api/download/windows-portable-lite-zip"
                        download="WikIranArchive_Portable_Windows_Release.zip"
                        className="py-2.5 px-4 text-xs sm:text-sm font-bold text-center text-slate-900 bg-sky-100 hover:bg-sky-200 border border-sky-300 rounded-lg transition-colors inline-flex items-center justify-center gap-2"
                      >
                        <Download className="w-4 h-4 shrink-0" />
                        <span>
                          {lang === 'fa'
                            ? 'نسخه سبک (~1 MB)'
                            : 'Fast Release (~1 MB)'}
                        </span>
                      </a>
                    </div>
                  </div>
                </div>
              </section>

              {/* SCHEDULED COLLECTION PANEL */}
              <form
                onSubmit={handleSaveSchedule}
                className="bg-white border-2 border-cyan-300 rounded-xl overflow-hidden shadow-xs"
              >
                <div className="bg-cyan-950 text-white px-5 sm:px-6 py-4 flex flex-wrap items-center justify-between gap-4">
                  <div className="space-y-1">
                    <div className="text-xs font-semibold text-cyan-300">
                      BACKGROUND TASK RUNNER · INCREMENTAL ARCHIVE SERVICE
                    </div>
                    <h3 className="text-base font-bold text-white">{t.schedulerTitle}</h3>
                    <p className="text-xs text-cyan-100">{t.schedulerSubtitle}</p>
                  </div>
                  <div className="text-xs font-mono-tabular bg-cyan-900 px-3 py-1.5 rounded border border-cyan-700">
                    Status: {data.schedule?.runner_status} · Next: {data.schedule?.next_run_at}
                  </div>
                </div>

                <div className="p-4 sm:p-6 space-y-5">
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
                    <div className="space-y-1.5">
                      <label className="block text-xs font-semibold text-slate-700">
                        {t.scheduleEnabledLabel}
                      </label>
                      <select
                        value={schedEnabled ? 'true' : 'false'}
                        onChange={(e) => setSchedEnabled(e.target.value === 'true')}
                        className="w-full px-3 py-2 text-xs border border-slate-300 rounded-md bg-white font-semibold"
                      >
                        <option value="true">Enabled (Active Background Runner)</option>
                        <option value="false">Paused (Manual Updates Only)</option>
                      </select>
                    </div>

                    <div className="space-y-1.5">
                      <label className="block text-xs font-semibold text-slate-700">
                        {t.scheduleFrequencyLabel}
                      </label>
                      <select
                        value={schedFreq}
                        onChange={(e) => setSchedFreq(e.target.value)}
                        className="w-full px-3 py-2 text-xs border border-slate-300 rounded-md bg-white"
                      >
                        <option value="daily">Daily (Every Day at Specified Time)</option>
                        <option value="weekly">Weekly (Selected Day of Week)</option>
                        <option value="every_6h">Every 6 Hours</option>
                        <option value="every_12h">Every 12 Hours</option>
                      </select>
                    </div>

                    <div className="space-y-1.5">
                      <label className="block text-xs font-semibold text-slate-700">
                        {t.scheduleTimeLabel}
                      </label>
                      <input
                        type="time"
                        value={schedTime}
                        onChange={(e) => setSchedTime(e.target.value)}
                        className="w-full px-3 py-2 text-xs border border-slate-300 rounded-md bg-white font-mono-tabular"
                      />
                    </div>

                    <div className="space-y-1.5">
                      <label className="block text-xs font-semibold text-slate-700">
                        {t.scheduleDayLabel}
                      </label>
                      <select
                        value={schedDay}
                        onChange={(e) => setSchedDay(e.target.value)}
                        disabled={schedFreq !== 'weekly'}
                        className="w-full px-3 py-2 text-xs border border-slate-300 rounded-md bg-white disabled:opacity-50"
                      >
                        <option value="sunday">Sunday</option>
                        <option value="monday">Monday</option>
                        <option value="tuesday">Tuesday</option>
                        <option value="wednesday">Wednesday</option>
                        <option value="thursday">Thursday</option>
                        <option value="friday">Friday</option>
                        <option value="saturday">Saturday</option>
                      </select>
                    </div>

                    <div className="space-y-1.5">
                      <label className="block text-xs font-semibold text-slate-700">
                        {t.scheduleMaxItemsLabel}
                      </label>
                      <input
                        type="number"
                        min={1}
                        max={25}
                        value={schedMaxItems}
                        onChange={(e) => setSchedMaxItems(Number(e.target.value))}
                        className="w-full px-3 py-2 text-xs border border-slate-300 rounded-md bg-white font-mono-tabular"
                      />
                    </div>
                  </div>

                  <div className="pt-2 border-t border-slate-100 flex flex-wrap items-center justify-between gap-4">
                    <div className="text-xs text-slate-500 font-mono-tabular">
                      Last Background Run: {data.schedule?.last_run_at} · Next Scheduled Run:{' '}
                      <span className="font-semibold text-cyan-900">
                        {data.schedule?.next_run_at}
                      </span>
                    </div>
                    <div className="flex flex-wrap items-center gap-3">
                      <button
                        type="button"
                        onClick={handleTriggerScheduledRunNow}
                        disabled={busyAction === 'schedule-run'}
                        className="px-4 py-2 text-xs font-semibold text-cyan-950 bg-cyan-100 border border-cyan-300 rounded-md hover:bg-cyan-200 transition-colors cursor-pointer"
                      >
                        {t.scheduleRunNowBtn}
                      </button>
                      <button
                        type="submit"
                        disabled={busyAction === 'schedule-save'}
                        className="px-4 py-2 text-xs font-semibold text-white bg-cyan-800 rounded-md hover:bg-cyan-900 transition-colors cursor-pointer"
                      >
                        {t.scheduleSaveBtn}
                      </button>
                    </div>
                  </div>
                </div>
              </form>

              {/* Archive Scope & Language Preferences */}
              <div className="bg-white border border-slate-200 rounded-lg p-4 sm:p-6 space-y-4">
                <h3 className="text-base font-bold text-slate-900">
                  {lang === 'fa'
                    ? 'تنظیمات دامنه استخراج، زبان و مسیر ذخیره‌سازی داده'
                    : 'Extraction Scope, Language & External AppData Storage'}
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                  <div className="p-4 border border-indigo-200 bg-indigo-50/40 rounded-md space-y-2">
                    <div className="text-xs font-bold text-indigo-950">
                      {lang === 'fa'
                        ? 'دامنه آرشیو و جستجو (ایمیل‌ها، فایل‌ها و اسناد بانکی)'
                        : 'Archive & Search Scope (Emails, Files & Banking)'}
                    </div>
                    <p className="text-xs text-slate-600">
                      {isFullUnredactedMode
                        ? lang === 'fa'
                          ? 'فعال: تمام ایمیل‌ها (/document/emails/*)، فایل‌ها و اسناد بانکی بدون حذفیات در دسترس هستند.'
                          : 'Active: All emails (/document/emails/*), raw files, and banking records are unlocked.'
                        : lang === 'fa'
                        ? 'فیلترشده: مکاتبات و اسناد بانکی مخفی هستند.'
                        : 'Filtered: Private correspondence and banking identifiers are filtered.'}
                    </p>
                    <button
                      onClick={() => handleToggleArchiveScope(!isFullUnredactedMode)}
                      className="px-3 py-1.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded cursor-pointer"
                    >
                      {isFullUnredactedMode ? t.switchToFilteredModeBtn : t.switchToFullModeBtn}
                    </button>
                  </div>

                  <div className="p-4 border border-slate-200 rounded-md space-y-2">
                    <div className="text-xs text-slate-500">Default Interface Language</div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleLanguageSwitch('en')}
                        className={`px-3 py-1.5 text-xs font-semibold rounded cursor-pointer ${
                          lang === 'en'
                            ? 'bg-indigo-600 text-white'
                            : 'bg-slate-100 text-slate-700'
                        }`}
                      >
                        English (LTR)
                      </button>
                      <button
                        onClick={() => handleLanguageSwitch('fa')}
                        className={`px-3 py-1.5 text-xs font-semibold rounded cursor-pointer ${
                          lang === 'fa'
                            ? 'bg-indigo-600 text-white'
                            : 'bg-slate-100 text-slate-700'
                        }`}
                      >
                        فارسی (RTL)
                      </button>
                    </div>
                  </div>

                  <div className="p-4 border border-slate-200 rounded-md space-y-1">
                    <div className="text-xs text-slate-500">External AppData Storage Path</div>
                    <div className="font-mono-tabular text-xs break-all text-slate-800">
                      {data.paths.db_path}
                    </div>
                  </div>
                </div>
              </div>

              {/* System Diagnostics, Reconnaissance & Source Code Inspector */}
              <div className="bg-white border border-slate-200 rounded-lg p-4 sm:p-6 space-y-5">
                <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 pb-4">
                  <div>
                    <h3 className="text-base font-bold text-slate-900">
                      System Diagnostics, Reconnaissance & Packaging Inspector
                    </h3>
                    <p className="text-xs text-slate-500">
                      Verify live reconnaissance, SQLite schema, Inno Setup script (installer/wikiran_archive_setup.iss), and automated unit tests.
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <button
                      onClick={handleRunRecon}
                      disabled={busyAction === 'recon'}
                      className="px-3.5 py-2 text-xs font-semibold text-slate-900 bg-slate-100 border border-slate-300 rounded-md hover:bg-slate-200 inline-flex items-center gap-1.5 cursor-pointer"
                    >
                      <Globe className="w-3.5 h-3.5" />
                      <span>{t.runReconBtn}</span>
                    </button>
                    <button
                      onClick={handleRunTests}
                      disabled={busyAction === 'tests'}
                      className="px-3.5 py-2 text-xs font-semibold text-white bg-emerald-800 rounded-md hover:bg-emerald-900 inline-flex items-center gap-1.5 cursor-pointer"
                    >
                      <Play className="w-3.5 h-3.5" />
                      <span>{t.runTestsBtn}</span>
                    </button>
                  </div>
                </div>

                {testOutput && (
                  <div className="bg-slate-950 text-emerald-400 p-4 rounded-md font-mono-tabular text-xs overflow-x-auto whitespace-pre">
                    {testOutput}
                  </div>
                )}

                <div className="flex flex-wrap items-center gap-2">
                  {[
                    { key: 'reconnaissance', label: 'RECONNAISSANCE_REPORT.md' },
                    { key: 'schema', label: 'DATABASE_SCHEMA.md (15 Tables)' },
                    { key: 'architecture', label: 'ARCHITECTURE.md' },
                    { key: 'status', label: 'PROJECT_STATUS.md' },
                    { key: 'pyside_ui', label: 'ui/main_window.py (PySide6)' },
                    { key: 'migrations_py', label: 'database/migrations.py' },
                    { key: 'recon_py', label: 'collector/reconnaissance.py' },
                  ].map((tab) => (
                    <button
                      key={tab.key}
                      onClick={() => loadDoc(tab.key)}
                      className={`px-3 py-1.5 text-xs font-mono-tabular rounded border transition-colors cursor-pointer ${
                        docKey === tab.key
                          ? 'bg-indigo-600 text-white border-indigo-600'
                          : 'bg-slate-50 text-slate-700 border-slate-300 hover:bg-slate-100'
                      }`}
                    >
                      <FileCode2 className="w-3 h-3 inline me-1" />
                      {tab.label}
                    </button>
                  ))}
                </div>

                {docContent && (
                  <div className="border border-slate-200 rounded-md overflow-hidden">
                    <div className="bg-slate-100 px-4 py-2 text-xs font-mono-tabular font-semibold text-slate-700 border-b border-slate-200">
                      {docContent.filename}
                    </div>
                    <pre className="p-4 bg-slate-50 text-xs font-mono-tabular text-slate-800 overflow-x-auto whitespace-pre-wrap max-h-96">
                      {docContent.content}
                    </pre>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* 10. HELP / OPERATOR MANUAL */}
          {activeNav === 'help' && (
            <div className="bg-white border border-slate-200 rounded-lg p-4 sm:p-6 space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-4">
                <h2 className="text-lg font-bold text-slate-900">
                  {lang === 'fa'
                    ? 'راهنمای کاربری برنامه (فارسی / انگلیسی)'
                    : 'User Guide & Reference Manual (English / Persian)'}
                </h2>
                <div className="flex flex-wrap items-center gap-2">
                  <button
                    onClick={() => setShowWorkflowModal(true)}
                    className="px-3 py-1.5 text-xs font-bold rounded bg-amber-400 text-slate-950 hover:bg-amber-300 cursor-pointer"
                  >
                    {t.howToWorkBtn}
                  </button>
                  <button
                    onClick={() => loadDoc('manual_en')}
                    className={`px-3 py-1.5 text-xs font-semibold rounded cursor-pointer ${
                      docKey === 'manual_en'
                        ? 'bg-indigo-600 text-white'
                        : 'bg-slate-100 text-slate-700'
                    }`}
                  >
                    OPERATOR_MANUAL_EN.md
                  </button>
                  <button
                    onClick={() => loadDoc('manual_fa')}
                    className={`px-3 py-1.5 text-xs font-semibold rounded cursor-pointer ${
                      docKey === 'manual_fa'
                        ? 'bg-indigo-600 text-white'
                        : 'bg-slate-100 text-slate-700'
                    }`}
                  >
                    OPERATOR_MANUAL_FA.md
                  </button>
                </div>
              </div>
              {docContent && (
                <pre className="text-sm text-slate-800 whitespace-pre-wrap leading-relaxed font-sans">
                  {docContent.content}
                </pre>
              )}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

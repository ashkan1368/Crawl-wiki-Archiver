import React, { useEffect, useState, useCallback } from 'react';
import {
  HardDriveDownload,
  RefreshCw,
  Square,
  ExternalLink,
  CheckSquare,
  Layers,
  Filter,
  Database,
  CheckCircle2,
} from 'lucide-react';
import { Language } from '../i18n';

interface LeakCollectionItem {
  slug: string;
  label: string;
  category: string;
  remote_count: number;
  remote_count_label: string;
  offline_count: number;
  last_page_synced: number;
  last_synced_at: string;
  source_url: string;
}

interface TargetedLeakDownloaderPanelProps {
  lang: Language;
  onDataUpdated: () => void;
}

const CATEGORIES = [
  'ALL',
  'Structured Archive',
  'Banking & Exchange',
  'Energy & Oil',
  'Shipping & Aviation',
  'Industrial & Government',
];

export const TargetedLeakDownloaderPanel: React.FC<TargetedLeakDownloaderPanelProps> = ({
  lang,
  onDataUpdated,
}) => {
  const isFa = lang === 'fa';
  const [collections, setCollections] = useState<LeakCollectionItem[]>([]);
  const [totalOfflineDocs, setTotalOfflineDocs] = useState<number>(0);
  const [loadingCatalog, setLoadingCatalog] = useState<boolean>(false);
  const [selectedSlugs, setSelectedSlugs] = useState<string[]>([]);
  const [categoryFilter, setCategoryFilter] = useState<string>('ALL');
  const [searchFilter, setSearchFilter] = useState<string>('');
  const [maxPages, setMaxPages] = useState<number>(15);
  const [keywordFilter, setKeywordFilter] = useState<string>('');
  const [startFromPage1, setStartFromPage1] = useState<boolean>(false);
  const [isDownloading, setIsDownloading] = useState<boolean>(false);
  const [statusBanner, setStatusBanner] = useState<string>('');
  const [errorBanner, setErrorBanner] = useState<string>('');
  const [liveProgress, setLiveProgress] = useState<{
    processed: number;
    newlyAdded: number;
  } | null>(null);

  const loadCatalog = useCallback(async (refreshRemote = false) => {
    setLoadingCatalog(true);
    setErrorBanner('');
    try {
      const res = await fetch(`/api/leaks/catalog${refreshRemote ? '?refresh=1' : ''}`);
      const json = await res.json();
      if (json.ok) {
        setCollections(json.collections || []);
        setTotalOfflineDocs(Number(json.total_offline_docs || 0));
      } else {
        setErrorBanner(json.error || 'Could not load leak collections catalog.');
      }
    } catch (err) {
      setErrorBanner(String(err));
    } finally {
      setLoadingCatalog(false);
    }
  }, []);

  useEffect(() => {
    loadCatalog(false);
  }, [loadCatalog]);

  // Poll live crawl progress while a targeted leak download is running
  useEffect(() => {
    if (!isDownloading) return;
    const timer = window.setInterval(async () => {
      try {
        const res = await fetch('/api/crawl-status');
        const json = await res.json();
        if (json.ok && json.active_job) {
          setLiveProgress({
            processed: Number(json.active_job.processed_count || 0),
            newlyAdded: Number(json.active_job.new_records_count || 0),
          });
        }
      } catch {
        // ignore transient poll error
      }
    }, 1800);
    return () => window.clearInterval(timer);
  }, [isDownloading]);

  const visibleCollections = collections.filter((c) => {
    if (categoryFilter !== 'ALL' && c.category !== categoryFilter) return false;
    if (searchFilter.trim()) {
      const q = searchFilter.trim().toLowerCase();
      if (!`${c.label} ${c.slug} ${c.category}`.toLowerCase().includes(q)) return false;
    }
    return true;
  });

  const toggleSlug = (slug: string) => {
    setSelectedSlugs((prev) =>
      prev.includes(slug) ? prev.filter((s) => s !== slug) : [...prev, slug]
    );
  };

  const selectAllVisible = () => {
    const visibleIds = visibleCollections.map((c) => c.slug);
    setSelectedSlugs((prev) => Array.from(new Set([...prev, ...visibleIds])));
  };

  const clearSelection = () => setSelectedSlugs([]);

  const handleDownloadSelected = async () => {
    if (selectedSlugs.length === 0) {
      setErrorBanner(
        isFa
          ? 'لطفاً حداقل یک مجموعه افشاگری را انتخاب کنید.'
          : 'Please select at least one leak collection to download.'
      );
      return;
    }

    setIsDownloading(true);
    setErrorBanner('');
    setStatusBanner('');
    setLiveProgress({ processed: 0, newlyAdded: 0 });

    try {
      const res = await fetch('/api/leaks/download', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          slugs: selectedSlugs,
          max_pages_per_leak: maxPages,
          keyword: keywordFilter.trim(),
          start_from_page_1: startFromPage1,
        }),
      });
      const json = await res.json();
      if (!json.ok) {
        setErrorBanner(json.error || 'Targeted leak download failed.');
      } else {
        if (json.catalog?.collections) {
          setCollections(json.catalog.collections);
          setTotalOfflineDocs(Number(json.catalog.total_offline_docs || 0));
        }
        setStatusBanner(
          isFa
            ? `تکمیل شد (${json.status}): ${Number(json.records_upserted || 0).toLocaleString()} سند پردازش شد (${Number(json.newly_added || 0).toLocaleString()} سند جدید در SQLite ذخیره و نمایه‌سازی شد) در ${json.pages_fetched || 0} صفحه.`
            : `Finished (${json.status}): Processed ${Number(json.records_upserted || 0).toLocaleString()} documents (${Number(json.newly_added || 0).toLocaleString()} newly saved & FTS5-indexed offline) across ${json.pages_fetched || 0} pages.`
        );
        onDataUpdated();
      }
    } catch (err) {
      setErrorBanner(String(err));
    } finally {
      setIsDownloading(false);
      setLiveProgress(null);
    }
  };

  const handleStopDownload = async () => {
    try {
      await fetch('/api/stop-crawl', { method: 'POST' });
      setStatusBanner(
        isFa
          ? 'درخواست توقف ایمن ارسال شد — نقطه بازیابی (Checkpoint) تا آخرین صفحه ذخیره‌شده حفظ می‌شود.'
          : 'Graceful stop requested — checkpoints are saved up to the latest completed batch.'
      );
    } catch {
      // ignore
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <section className="bg-slate-900 text-white rounded-xl border border-slate-800 p-5 sm:p-6 shadow-xs">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="space-y-1.5 max-w-3xl">
            <div className="text-xs font-bold uppercase tracking-wider text-sky-400">
              {isFa
                ? 'دانلودر هدفمند و مرحله‌به‌مرحله مجموعه‌های افشاگری ویکی‌ایران'
                : 'TARGETED LEAK ARCHIVE DOWNLOADER (CHECKPOINT-RESUMABLE)'}
            </div>
            <h2 className="text-lg sm:text-xl font-bold text-white">
              {isFa
                ? 'انتخاب دقیق آرشیوهای مرتبط با حوزه کاری شما برای ذخیره آفلاین'
                : 'Archive Specific WikIran Leak Collections Offline at Your Own Pace'}
            </h2>
            <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
              {isFa
                ? 'به‌جای دانلود کورکورانه ۳.۱ میلیون صفحه، فقط مجموعه‌هایی را انتخاب کنید که به تجارت شما مربوط هستند (مثلاً صرافی‌ها، بانک سپه یا شرکت‌های پتروشیمی). برنامه صفحه توقف هر مجموعه را ذخیره می‌کند تا در نوبت بعدی دقیقاً از ادامه آن دانلود شود.'
                : 'Instead of blindly crawling 3.1 million emails, pick only the leak collections relevant to your trade sector (e.g., Exchange Houses, Bank Sepah, Shipping, or Petrochemicals). Every leak remembers its saved page checkpoint so you can resume right where you left off anytime.'}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3 shrink-0">
            <div className="bg-slate-950 border border-slate-700 rounded-lg px-4 py-2 text-right">
              <div className="text-[11px] text-slate-400">
                {isFa ? 'اسناد ویکی‌ایران ذخیره آفلاین' : 'WikIran Docs Offline'}
              </div>
              <div className="text-lg font-bold font-mono-tabular text-emerald-400">
                {totalOfflineDocs.toLocaleString()}
              </div>
            </div>
            <button
              type="button"
              disabled={loadingCatalog}
              onClick={() => loadCatalog(true)}
              className="px-4 py-2.5 text-xs font-bold text-slate-100 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg transition-colors inline-flex items-center gap-2 cursor-pointer"
            >
              <RefreshCw className={`w-4 h-4 ${loadingCatalog ? 'animate-spin' : ''}`} />
              <span>{isFa ? 'بروزرسانی آمار از سایت' : 'Refresh Live Counts'}</span>
            </button>
          </div>
        </div>
      </section>

      {/* Download Controls Bar */}
      <section className="bg-white border-2 border-sky-200 rounded-xl p-5 shadow-xs space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Batch Size */}
          <div className="space-y-1.5">
            <label className="block text-xs font-bold text-slate-700">
              {isFa ? 'تعداد صفحات در هر نوبت (برای هر مجموعه):' : 'Batch Size (Pages per Selected Leak):'}
            </label>
            <select
              value={maxPages}
              onChange={(e) => setMaxPages(Number(e.target.value))}
              className="w-full px-3 py-2 text-xs font-semibold border border-slate-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-sky-600"
            >
              <option value={5}>{isFa ? '۵ صفحه (~۵۰ سند — سریع)' : '5 pages (~50 docs/leak — Quick test)'}</option>
              <option value={15}>{isFa ? '۱۵ صفحه (~۱۵۰ سند — پیشنهادی)' : '15 pages (~150 docs/leak — Recommended)'}</option>
              <option value={50}>{isFa ? '۵۰ صفحه (~۵۰۰ سند)' : '50 pages (~500 docs/leak — Deep batch)'}</option>
              <option value={100}>{isFa ? '۱۰۰ صفحه (~۱٬۰۰۰ سند)' : '100 pages (~1,000 docs/leak — Heavy batch)'}</option>
              <option value={250}>{isFa ? '۲۵۰ صفحه (~۲٬۵۰۰ سند)' : '250 pages (~2,500 docs/leak — Max batch)'}</option>
            </select>
          </div>

          {/* Optional Keyword Filter */}
          <div className="space-y-1.5">
            <label className="block text-xs font-bold text-slate-700">
              {isFa ? 'فیلتر کلمه کلیدی داخل افشاگری (اختیاری):' : 'Optional Keyword Filter Inside Leak(s):'}
            </label>
            <input
              type="text"
              value={keywordFilter}
              onChange={(e) => setKeywordFilter(e.target.value)}
              placeholder={
                isFa
                  ? 'مثلاً: oil یا steel یا bank (خالی = همه اسناد)'
                  : 'e.g. oil, steel, invoice, tanker (blank = all docs)'
              }
              className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-sky-600"
            />
          </div>

          {/* Resume Mode */}
          <div className="flex flex-col justify-end space-y-2">
            <label className="flex items-center gap-2 text-xs text-slate-700 cursor-pointer">
              <input
                type="checkbox"
                checked={startFromPage1}
                onChange={(e) => setStartFromPage1(e.target.checked)}
                className="rounded border-slate-300 text-sky-600 focus:ring-sky-600"
              />
              <span>
                {isFa
                  ? 'شروع مجدد از صفحه ۱ (به‌جای ادامه از Checkpoint)'
                  : 'Restart from Page 1 (instead of resuming checkpoint)'}
              </span>
            </label>
          </div>
        </div>

        <div className="pt-3 border-t border-slate-200 flex flex-wrap items-center justify-between gap-3">
          <div className="text-xs font-semibold text-slate-700 flex items-center gap-2">
            <CheckSquare className="w-4 h-4 text-sky-600" />
            <span>
              {isFa
                ? `${selectedSlugs.length} مجموعه انتخاب شده`
                : `${selectedSlugs.length} leak collection(s) selected`}
            </span>
            {selectedSlugs.length > 0 && (
              <button
                type="button"
                onClick={clearSelection}
                className="text-rose-700 hover:underline font-bold cursor-pointer"
              >
                {isFa ? '(پاک کردن انتخاب)' : '(Clear)'}
              </button>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {isDownloading && (
              <button
                type="button"
                onClick={handleStopDownload}
                className="px-4 py-2.5 text-xs font-bold text-white bg-rose-600 hover:bg-rose-700 rounded-lg transition-colors inline-flex items-center gap-1.5 cursor-pointer"
              >
                <Square className="w-3.5 h-3.5 fill-current" />
                <span>{isFa ? 'توقف و ذخیره Checkpoint' : 'Stop & Save Checkpoint'}</span>
              </button>
            )}
            <button
              type="button"
              disabled={isDownloading || selectedSlugs.length === 0}
              onClick={handleDownloadSelected}
              className="px-5 py-2.5 text-xs sm:text-sm font-bold text-white bg-sky-700 hover:bg-sky-800 disabled:opacity-50 rounded-lg transition-colors inline-flex items-center gap-2 shadow-xs cursor-pointer"
            >
              {isDownloading ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>
                    {isFa
                      ? `در حال دانلود... (${liveProgress?.newlyAdded ?? 0} جدید)`
                      : `Downloading... (${liveProgress?.processed ?? 0} processed, ${liveProgress?.newlyAdded ?? 0} new)`}
                  </span>
                </>
              ) : (
                <>
                  <HardDriveDownload className="w-4 h-4" />
                  <span>
                    {isFa
                      ? 'دانلود آفلاین مجموعه‌های انتخاب‌شده'
                      : 'Download Selected Leak(s) Offline'}
                  </span>
                </>
              )}
            </button>
          </div>
        </div>

        {statusBanner && (
          <div className="p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-xs text-emerald-900 font-medium flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>{statusBanner}</span>
          </div>
        )}

        {errorBanner && (
          <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-800 font-medium">
            {errorBanner}
          </div>
        )}
      </section>

      {/* Leak Collection Selector Table */}
      <section className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-xs">
        <div className="px-4 py-3 bg-slate-50 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-1.5">
            <Filter className="w-3.5 h-3.5 text-slate-500 mr-1" />
            {CATEGORIES.map((cat) => (
              <button
                key={cat}
                type="button"
                onClick={() => setCategoryFilter(cat)}
                className={`px-2.5 py-1 text-[11px] font-bold rounded-md transition-colors cursor-pointer ${
                  categoryFilter === cat
                    ? 'bg-slate-900 text-white'
                    : 'bg-white text-slate-700 border border-slate-300 hover:bg-slate-100'
                }`}
              >
                {cat === 'ALL' ? (isFa ? 'همه دسته‌ها' : 'All Sectors') : cat}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
              placeholder={isFa ? 'جستجوی نام مجموعه...' : 'Filter leaks...'}
              className="px-3 py-1.5 text-xs border border-slate-300 rounded-md w-48 bg-white focus:outline-none focus:ring-2 focus:ring-sky-600"
            />
            <button
              type="button"
              onClick={selectAllVisible}
              className="px-2.5 py-1.5 text-xs font-bold text-sky-800 bg-sky-50 hover:bg-sky-100 border border-sky-200 rounded-md cursor-pointer whitespace-nowrap"
            >
              {isFa ? 'انتخاب همه' : 'Select Visible'}
            </button>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left border-collapse">
            <thead className="bg-slate-100 text-slate-700 border-b border-slate-200">
              <tr>
                <th className="px-3.5 py-2.5 w-10"></th>
                <th className="px-3.5 py-2.5 font-bold">{isFa ? 'مجموعه افشاگری' : 'WikIran Leak Collection'}</th>
                <th className="px-3.5 py-2.5 font-bold">{isFa ? 'حوزه' : 'Sector'}</th>
                <th className="px-3.5 py-2.5 font-bold text-right">{isFa ? 'تعداد در سایت' : 'On WikIran'}</th>
                <th className="px-3.5 py-2.5 font-bold text-right">{isFa ? 'ذخیره آفلاین ما' : 'Saved Offline'}</th>
                <th className="px-3.5 py-2.5 font-bold text-center">{isFa ? 'نقطه توقف (Checkpoint)' : 'Checkpoint Page'}</th>
                <th className="px-3.5 py-2.5 font-bold text-center">{isFa ? 'لینک' : 'Link'}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {visibleCollections.map((col) => {
                const isSelected = selectedSlugs.includes(col.slug);
                const pct =
                  col.remote_count > 0
                    ? Math.min(100, Math.round((col.offline_count / col.remote_count) * 100))
                    : col.offline_count > 0
                    ? 100
                    : 0;

                return (
                  <tr
                    key={col.slug}
                    onClick={() => toggleSlug(col.slug)}
                    className={`cursor-pointer transition-colors ${
                      isSelected ? 'bg-sky-50/80' : 'hover:bg-slate-50'
                    }`}
                  >
                    <td className="px-3.5 py-3 text-center">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => {}}
                        className="rounded border-slate-300 text-sky-600 focus:ring-sky-600 cursor-pointer"
                      />
                    </td>
                    <td className="px-3.5 py-3">
                      <div className="font-bold text-slate-900">{col.label}</div>
                      <div className="text-[11px] font-mono-tabular text-slate-500">
                        slug: {col.slug}
                      </div>
                    </td>
                    <td className="px-3.5 py-3">
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-semibold text-[11px]">
                        <Layers className="w-3 h-3 text-slate-500" />
                        {col.category}
                      </span>
                    </td>
                    <td className="px-3.5 py-3 text-right font-mono-tabular font-bold text-slate-700">
                      {col.remote_count_label}
                    </td>
                    <td className="px-3.5 py-3 text-right">
                      <div className="inline-flex flex-col items-end gap-1 min-w-[96px]">
                        <span
                          className={`font-mono-tabular font-bold inline-flex items-center gap-1 ${
                            col.offline_count > 0 ? 'text-emerald-700' : 'text-slate-400'
                          }`}
                        >
                          <Database className="w-3 h-3" />
                          {col.offline_count.toLocaleString()}
                        </span>
                        <div className="w-24 h-1.5 bg-slate-200 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-emerald-500 rounded-full"
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </div>
                    </td>
                    <td className="px-3.5 py-3 text-center font-mono-tabular">
                      {col.last_page_synced > 0 ? (
                        <span className="px-2 py-0.5 rounded bg-indigo-50 text-indigo-800 font-bold text-[11px]">
                          Page {col.last_page_synced}
                        </span>
                      ) : (
                        <span className="text-slate-400 text-[11px]">—</span>
                      )}
                    </td>
                    <td className="px-3.5 py-3 text-center">
                      <a
                        href={col.source_url}
                        target="_blank"
                        rel="noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="text-sky-700 hover:text-sky-900 inline-flex items-center justify-center p-1"
                        title={col.source_url}
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                      </a>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
};

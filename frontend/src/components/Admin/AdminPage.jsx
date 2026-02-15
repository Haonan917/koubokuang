import React, { useEffect, useMemo, useState } from 'react';
import { adminListCookiePool, adminCreateCookiePoolItem, adminDeleteCookiePoolItem, adminListUsers, adminUpdateUser, adminLLMUsageSummary } from '../../services/admin';

function TabButton({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-2 text-sm rounded-lg border transition-colors ${
        active ? 'bg-primary/10 text-primary border-primary/20' : 'bg-transparent text-text-secondary border-border-default hover:bg-white/5 hover:text-text-primary'
      }`}
    >
      {children}
    </button>
  );
}

function Section({ title, children, right }) {
  return (
    <div className="bg-bg-secondary border border-border-default rounded-2xl overflow-hidden">
      <div className="px-5 py-4 border-b border-border-default flex items-center justify-between">
        <div className="text-sm font-semibold text-text-primary">{title}</div>
        <div>{right}</div>
      </div>
      <div className="p-5">{children}</div>
    </div>
  );
}

function Table({ columns, rows, rowKey }) {
  return (
    <div className="overflow-auto rounded-xl border border-border-default">
      <table className="min-w-full text-sm">
        <thead className="bg-black/10">
          <tr>
            {columns.map((c) => (
              <th key={c.key} className="text-left font-medium text-text-secondary px-3 py-2 whitespace-nowrap">
                {c.title}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={rowKey(r)} className="border-t border-border-default/70">
              {columns.map((c) => (
                <td key={c.key} className="px-3 py-2 text-text-primary align-top whitespace-nowrap">
                  {typeof c.render === 'function' ? c.render(r) : r[c.key]}
                </td>
              ))}
            </tr>
          ))}
          {rows.length === 0 && (
            <tr>
              <td colSpan={columns.length} className="px-3 py-8 text-center text-text-muted">
                No data
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

function CookiesPoolTab() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [platform, setPlatform] = useState('xhs');
  const [accountName, setAccountName] = useState('admin');
  const [cookies, setCookies] = useState('');
  const [error, setError] = useState(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await adminListCookiePool({ limit: 200 });
      setItems(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const onCreate = async () => {
    if (!cookies.trim()) return;
    setError(null);
    try {
      await adminCreateCookiePoolItem({ platform_name: platform, account_name: accountName.trim(), cookies: cookies.trim() });
      setCookies('');
      await load();
    } catch (e) {
      setError(e.message);
    }
  };

  const onDelete = async (id) => {
    if (!confirm(`Delete cookie pool item #${id}?`)) return;
    setError(null);
    try {
      await adminDeleteCookiePoolItem(id);
      await load();
    } catch (e) {
      setError(e.message);
    }
  };

  const columns = useMemo(() => [
    { key: 'id', title: 'ID' },
    { key: 'platform_name', title: 'Platform' },
    { key: 'account_name', title: 'Account' },
    { key: 'status', title: 'Status' },
    { key: 'invalid_timestamp', title: 'InvalidTs' },
    { key: 'update_time', title: 'Updated' },
    { key: 'actions', title: 'Actions', render: (r) => (
      <button className="text-red-400 hover:text-red-300" onClick={() => onDelete(r.id)}>Delete</button>
    ) },
  ], [items]);

  return (
    <div className="space-y-4">
      <Section
        title="Cookies Pool"
        right={<button onClick={load} className="text-sm px-3 py-2 rounded-lg border border-border-default hover:bg-white/5">{loading ? 'Loading...' : 'Refresh'}</button>}
      >
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div className="flex flex-col gap-1">
            <div className="text-xs text-text-muted">Platform</div>
            <select value={platform} onChange={(e) => setPlatform(e.target.value)} className="px-3 py-2 rounded-lg bg-bg-primary border border-border-default">
              <option value="xhs">xhs</option>
              <option value="dy">dy</option>
              <option value="ks">ks</option>
              <option value="bili">bili</option>
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <div className="text-xs text-text-muted">Account</div>
            <input value={accountName} onChange={(e) => setAccountName(e.target.value)} className="px-3 py-2 rounded-lg bg-bg-primary border border-border-default" />
          </div>
          <div className="flex items-end">
            <button onClick={onCreate} className="w-full px-3 py-2 rounded-lg bg-primary text-white hover:bg-primary/90">Add</button>
          </div>
        </div>
        <div className="mt-3">
          <div className="text-xs text-text-muted mb-1">Cookies</div>
          <textarea value={cookies} onChange={(e) => setCookies(e.target.value)} rows={4} className="w-full px-3 py-2 rounded-lg bg-bg-primary border border-border-default font-mono text-xs" />
        </div>
        {error && <div className="mt-3 text-sm text-red-400">{error}</div>}
        <div className="mt-4">
          <Table columns={columns} rows={items} rowKey={(r) => r.id} />
        </div>
      </Section>
    </div>
  );
}

function UsersTab() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [q, setQ] = useState('');

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await adminListUsers({ q: q.trim() || undefined, limit: 200 });
      setRows(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const setDisabled = async (userId, disabled) => {
    setError(null);
    try {
      await adminUpdateUser(userId, { status: disabled ? 2 : 1 });
      await load();
    } catch (e) {
      setError(e.message);
    }
  };

  const setAdmin = async (userId, isAdmin) => {
    setError(null);
    try {
      await adminUpdateUser(userId, { is_admin: isAdmin ? 1 : 0 });
      await load();
    } catch (e) {
      setError(e.message);
    }
  };

  const columns = useMemo(() => [
    { key: 'email', title: 'Email' },
    { key: 'display_name', title: 'Name' },
    { key: 'status', title: 'Status' },
    { key: 'is_admin', title: 'Admin' },
    { key: 'actions', title: 'Actions', render: (r) => (
      <div className="flex gap-2">
        <button className="text-sm px-2 py-1 rounded border border-border-default hover:bg-white/5" onClick={() => setDisabled(r.user_id, r.status !== 2)}>
          {r.status === 2 ? 'Enable' : 'Disable'}
        </button>
        <button className="text-sm px-2 py-1 rounded border border-border-default hover:bg-white/5" onClick={() => setAdmin(r.user_id, r.is_admin !== 1)}>
          {r.is_admin === 1 ? 'Unset admin' : 'Set admin'}
        </button>
      </div>
    ) },
  ], [rows]);

  return (
    <div className="space-y-4">
      <Section
        title="Users"
        right={(
          <div className="flex gap-2">
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="search email/name" className="px-3 py-2 rounded-lg bg-bg-primary border border-border-default text-sm" />
            <button onClick={load} className="text-sm px-3 py-2 rounded-lg border border-border-default hover:bg-white/5">{loading ? 'Loading...' : 'Search'}</button>
          </div>
        )}
      >
        {error && <div className="mb-3 text-sm text-red-400">{error}</div>}
        <Table columns={columns} rows={rows} rowKey={(r) => r.user_id} />
      </Section>
    </div>
  );
}

function UsageTab() {
  const [days, setDays] = useState(7);
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await adminLLMUsageSummary({ days: Number(days) || 7 });
      setRows(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const columns = useMemo(() => [
    { key: 'day', title: 'Day' },
    { key: 'model', title: 'Model' },
    { key: 'calls', title: 'Calls' },
    { key: 'input_tokens', title: 'In' },
    { key: 'output_tokens', title: 'Out' },
    { key: 'total_tokens', title: 'Total' },
    { key: 'estimated_cost_usd', title: 'Cost(USD)' },
  ], [rows]);

  return (
    <div className="space-y-4">
      <Section
        title="LLM Usage Summary"
        right={(
          <div className="flex gap-2 items-center">
            <input value={days} onChange={(e) => setDays(e.target.value)} className="w-20 px-3 py-2 rounded-lg bg-bg-primary border border-border-default text-sm" />
            <button onClick={load} className="text-sm px-3 py-2 rounded-lg border border-border-default hover:bg-white/5">{loading ? 'Loading...' : 'Refresh'}</button>
          </div>
        )}
      >
        {error && <div className="mb-3 text-sm text-red-400">{error}</div>}
        <Table columns={columns} rows={rows} rowKey={(r) => `${r.day}-${r.model}`} />
      </Section>
    </div>
  );
}

export default function AdminPage() {
  const [tab, setTab] = useState('cookies');

  return (
    <div className="min-h-screen bg-bg-primary text-text-primary">
      <div className="max-w-6xl mx-auto px-6 py-6 space-y-5">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-lg font-semibold">Admin Console</div>
            <div className="text-sm text-text-muted">Cookies / Users / Usage</div>
          </div>
          <div className="flex gap-2">
            <TabButton active={tab === 'cookies'} onClick={() => setTab('cookies')}>Cookies</TabButton>
            <TabButton active={tab === 'users'} onClick={() => setTab('users')}>Users</TabButton>
            <TabButton active={tab === 'usage'} onClick={() => setTab('usage')}>Usage</TabButton>
          </div>
        </div>

        {tab === 'cookies' && <CookiesPoolTab />}
        {tab === 'users' && <UsersTab />}
        {tab === 'usage' && <UsageTab />}
      </div>
    </div>
  );
}

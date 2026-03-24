import { useState, useEffect } from 'react';
import {
  BarChart, Bar,
  LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import {
  getAnalyticsSummary,
  getLowRotationItems,
  getOrdersByHour,
  getRevenuePerDay,
  getRevenuePerWorkstation,
} from '../../services/analyticsService';
import './Analytics.css';

function todayIsoDate() {
  const now = new Date();
  const local = new Date(now.getTime() - now.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 10);
}

/**
 * Analytics - Daily dashboard snapshot for admin users
 *
 * Shows:
 *  - 5 KPI cards (revenue, avg ticket, orders, busiest station, peak hour)
 *  - Top 3 items of the day ranked list
 *  - Loading skeleton and empty state
 */
function Analytics() {
  const [activeTab, setActiveTab] = useState('overview');
  const [fromDate, setFromDate] = useState(todayIsoDate());
  const [toDate, setToDate] = useState(todayIsoDate());

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [revenuePerDayData, setRevenuePerDayData] = useState([]);
  const [revenuePerDayLoading, setRevenuePerDayLoading] = useState(false);
  const [revenuePerDayError, setRevenuePerDayError] = useState(null);
  const [revenuePerDayLoaded, setRevenuePerDayLoaded] = useState(false);

  const [revenuePerWorkstationData, setRevenuePerWorkstationData] = useState([]);
  const [revenuePerWorkstationLoading, setRevenuePerWorkstationLoading] = useState(false);
  const [revenuePerWorkstationError, setRevenuePerWorkstationError] = useState(null);
  const [revenuePerWorkstationLoaded, setRevenuePerWorkstationLoaded] = useState(false);

  const [ordersByHourData, setOrdersByHourData] = useState([]);
  const [ordersByHourLoading, setOrdersByHourLoading] = useState(false);
  const [ordersByHourError, setOrdersByHourError] = useState(null);
  const [ordersByHourLoaded, setOrdersByHourLoaded] = useState(false);

  const [lowRotationItemsData, setLowRotationItemsData] = useState([]);
  const [lowRotationItemsLoading, setLowRotationItemsLoading] = useState(false);
  const [lowRotationItemsError, setLowRotationItemsError] = useState(null);
  const [lowRotationItemsLoaded, setLowRotationItemsLoaded] = useState(false);

  useEffect(() => {
    loadSummary(fromDate, toDate);
    setRevenuePerDayLoaded(false);
    setRevenuePerWorkstationLoaded(false);
    setOrdersByHourLoaded(false);
    setLowRotationItemsLoaded(false);

    if (activeTab === 'revenue-per-day') {
      loadRevenuePerDay(fromDate, toDate);
    }
    if (activeTab === 'revenue-per-workstation') {
      loadRevenuePerWorkstation(fromDate, toDate);
    }
    if (activeTab === 'orders-by-hour') {
      loadOrdersByHour(fromDate, toDate);
    }
    if (activeTab === 'low-rotation-items') {
      loadLowRotationItems(fromDate, toDate);
    }
  }, [fromDate, toDate]);

  useEffect(() => {
    if (activeTab === 'revenue-per-day' && !revenuePerDayLoaded) {
      loadRevenuePerDay();
    }
    if (activeTab === 'revenue-per-workstation' && !revenuePerWorkstationLoaded) {
      loadRevenuePerWorkstation();
    }
    if (activeTab === 'orders-by-hour' && !ordersByHourLoaded) {
      loadOrdersByHour();
    }
    if (activeTab === 'low-rotation-items' && !lowRotationItemsLoaded) {
      loadLowRotationItems();
    }
  }, [activeTab]);

  const loadSummary = async (from = fromDate, to = toDate) => {
    try {
      setLoading(true);
      setError(null);
      const summary = await getAnalyticsSummary(from, to);
      setData(summary);
    } catch (err) {
      console.error('[Analytics] Αποτυχία φόρτωσης:', err);
      setError(err.message || 'Αποτυχία φόρτωσης στατιστικών στοιχείων');
    } finally {
      setLoading(false);
    }
  };

  const loadRevenuePerDay = async (from = fromDate, to = toDate) => {
    try {
      setRevenuePerDayLoading(true);
      setRevenuePerDayError(null);
      const rows = await getRevenuePerDay(from, to);
      setRevenuePerDayData(rows || []);
      setRevenuePerDayLoaded(true);
    } catch (err) {
      console.error('[Analytics] Αποτυχία φόρτωσης ανά ημέρα:', err);
      setRevenuePerDayError(err.message || 'Αποτυχία φόρτωσης εσόδων ανά ημέρα');
    } finally {
      setRevenuePerDayLoading(false);
    }
  };

  const loadRevenuePerWorkstation = async (from = fromDate, to = toDate) => {
    try {
      setRevenuePerWorkstationLoading(true);
      setRevenuePerWorkstationError(null);
      const rows = await getRevenuePerWorkstation(from, to);
      setRevenuePerWorkstationData(rows || []);
      setRevenuePerWorkstationLoaded(true);
    } catch (err) {
      console.error('[Analytics] Αποτυχία φόρτωσης ανά πόστο:', err);
      setRevenuePerWorkstationError(err.message || 'Αποτυχία φόρτωσης εσόδων ανά πόστο');
    } finally {
      setRevenuePerWorkstationLoading(false);
    }
  };

  const loadOrdersByHour = async (from = fromDate, to = toDate) => {
    try {
      setOrdersByHourLoading(true);
      setOrdersByHourError(null);
      const rows = await getOrdersByHour(from, to);
      setOrdersByHourData(rows || []);
      setOrdersByHourLoaded(true);
    } catch (err) {
      console.error('[Analytics] Αποτυχία φόρτωσης ανά ώρα:', err);
      setOrdersByHourError(err.message || 'Αποτυχία φόρτωσης παραγγελιών ανά ώρα');
    } finally {
      setOrdersByHourLoading(false);
    }
  };

  const loadLowRotationItems = async (from = fromDate, to = toDate) => {
    try {
      setLowRotationItemsLoading(true);
      setLowRotationItemsError(null);
      const rows = await getLowRotationItems(from, to);
      setLowRotationItemsData(rows || []);
      setLowRotationItemsLoaded(true);
    } catch (err) {
      console.error('[Analytics] Αποτυχία φόρτωσης ειδών χαμηλής κυκλοφορίας:', err);
      setLowRotationItemsError(err.message || 'Αποτυχία φόρτωσης ειδών χαμηλής κυκλοφορίας');
    } finally {
      setLowRotationItemsLoading(false);
    }
  };

  const renderOverview = () => {
    if (loading) {
      return (
        <>
          <div className="analytics-kpi-grid" aria-busy="true" aria-label="Φόρτωση">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="analytics-kpi-card analytics-skeleton" />
            ))}
          </div>
          <div className="analytics-top-items">
            <div className="analytics-skeleton analytics-skeleton-title" />
            {[1, 2, 3].map((i) => (
              <div key={i} className="analytics-skeleton analytics-skeleton-row" />
            ))}
          </div>
        </>
      );
    }

    if (error) {
      return (
        <>
          <div className="alert alert-error">⚠️ {error}</div>
          <button className="analytics-retry-btn" onClick={loadSummary}>
            Επανάληψη
          </button>
        </>
      );
    }

    const isEmpty = !data || data.orders_count === 0;

    return (
      <>
        {/* KPI Cards */}
        <div className="analytics-kpi-grid">
          <div className="analytics-kpi-card">
            <span className="analytics-kpi-icon">💰</span>
            <span className="analytics-kpi-label">Έσοδα Σήμερα</span>
            <span className="analytics-kpi-value">
              {isEmpty ? '—' : `€${Number(data.today_revenue).toFixed(2)}`}
            </span>
            {!isEmpty && data.revenue_change_vs_previous_day !== 0 && (
              <span
                className={`analytics-kpi-change ${
                  data.revenue_change_vs_previous_day >= 0 ? 'positive' : 'negative'
                }`}
              >
                {`${data.revenue_change_vs_previous_day >= 0 ? '▲' : '▼'}${Math.abs(data.revenue_change_vs_previous_day).toFixed(1)}%`}
              </span>
            )}
          </div>

          <div className="analytics-kpi-card">
            <span className="analytics-kpi-icon">🧾</span>
            <span className="analytics-kpi-label">Μέση Αξία Παραγγελίας</span>
            <span className="analytics-kpi-value">
              {isEmpty ? '—' : `€${Number(data.average_ticket_size).toFixed(2)}`}
            </span>
          </div>

          <div className="analytics-kpi-card">
            <span className="analytics-kpi-icon">📋</span>
            <span className="analytics-kpi-label">Αριθμός Παραγγελιών</span>
            <span className="analytics-kpi-value">
              {data ? data.orders_count : '—'}
            </span>
          </div>

          <div className="analytics-kpi-card">
            <span className="analytics-kpi-icon">🍳</span>
            <span className="analytics-kpi-label">Πιο Πολυάσχολο Πόστο</span>
            <span className="analytics-kpi-value analytics-kpi-value--text">
              {isEmpty || !data.busiest_workstation ? '—' : data.busiest_workstation}
            </span>
          </div>

          <div className="analytics-kpi-card">
            <span className="analytics-kpi-icon">🕐</span>
            <span className="analytics-kpi-label">Ώρα Αιχμής</span>
            <span className="analytics-kpi-value analytics-kpi-value--text">
              {isEmpty || !data.peak_hour ? '—' : data.peak_hour}
            </span>
          </div>
        </div>

        {/* Top 3 Items */}
        <div className="analytics-top-items">
          <h3 className="analytics-top-items-title">🏆 Κορυφαία 3 Προϊόντα</h3>

          {isEmpty ? (
            <div className="analytics-empty-state">
              <span className="analytics-empty-icon">🍽️</span>
              <p className="analytics-empty-text">
                Δεν υπάρχουν δεδομένα παραγγελιών για σήμερα.
              </p>
              <p className="analytics-empty-subtext">
                Τα στατιστικά στοιχεία θα εμφανιστούν μόλις ολοκληρωθούν οι πρώτες παραγγελίες.
              </p>
            </div>
          ) : (
            <ol className="analytics-top-items-list">
              {(data.top_items_today || []).slice(0, 3).map((item, index) => (
                <li key={item.name} className="analytics-top-item">
                  <span className="analytics-top-item-rank">#{index + 1}</span>
                  <span className="analytics-top-item-name">{item.name}</span>
                  <span className="analytics-top-item-qty">{item.qty} τεμ.</span>
                </li>
              ))}
            </ol>
          )}
        </div>
      </>
    );
  };

  const renderRevenuePerDay = () => {
    if (revenuePerDayLoading) {
      return <div className="analytics-tab-loading" aria-label="Φόρτωση ανά ημέρα">Φόρτωση...</div>;
    }
    if (revenuePerDayError) {
      return (
        <div className="analytics-tab-feedback">
          <div className="alert alert-error">⚠️ {revenuePerDayError}</div>
          <button className="analytics-retry-btn" onClick={loadRevenuePerDay}>Επανάληψη</button>
        </div>
      );
    }
    if (!revenuePerDayData.length) {
      return <div className="analytics-tab-empty">Δεν υπάρχουν δεδομένα εσόδων για την επιλεγμένη περίοδο.</div>;
    }

    return (
      <div className="analytics-chart-wrap" aria-label="Γράφημα εσόδων ανά μέρα">
        <ResponsiveContainer width="100%" height={300}>
          <BarChart
            data={revenuePerDayData.map((r) => ({ date: r.date, revenue: Number(r.revenue) }))}
            margin={{ top: 16, right: 24, left: 8, bottom: 56 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis dataKey="date" tick={{ fontSize: 11 }} angle={-35} textAnchor="end" interval={0} />
            <YAxis tickFormatter={(v) => `€${v}`} tick={{ fontSize: 11 }} />
            <Tooltip formatter={(v) => [`€${Number(v).toFixed(2)}`, 'Έσοδα']} />
            <Bar dataKey="revenue" fill="#667eea" radius={[4, 4, 0, 0]} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    );
  };

  const renderRevenuePerWorkstation = () => {
    if (revenuePerWorkstationLoading) {
      return <div className="analytics-tab-loading" aria-label="Φόρτωση ανά πόστο">Φόρτωση...</div>;
    }
    if (revenuePerWorkstationError) {
      return (
        <div className="analytics-tab-feedback">
          <div className="alert alert-error">⚠️ {revenuePerWorkstationError}</div>
          <button className="analytics-retry-btn" onClick={loadRevenuePerWorkstation}>Επανάληψη</button>
        </div>
      );
    }
    if (!revenuePerWorkstationData.length) {
      return <div className="analytics-tab-empty">Δεν υπάρχουν δεδομένα εσόδων ανά πόστο για την επιλεγμένη περίοδο.</div>;
    }

    return (
      <div className="analytics-chart-wrap" aria-label="Γράφημα εσόδων ανά πόστο">
        <ResponsiveContainer width="100%" height={300}>
          <BarChart
            data={revenuePerWorkstationData.map((r) => ({ workstation: r.workstation, revenue: Number(r.revenue) }))}
            margin={{ top: 16, right: 24, left: 8, bottom: 24 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis dataKey="workstation" tick={{ fontSize: 12 }} />
            <YAxis tickFormatter={(v) => `€${v}`} tick={{ fontSize: 11 }} />
            <Tooltip formatter={(v) => [`€${Number(v).toFixed(2)}`, 'Έσοδα']} />
            <Bar dataKey="revenue" fill="#764ba2" radius={[4, 4, 0, 0]} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    );
  };

  const renderOrdersByHour = () => {
    if (ordersByHourLoading) {
      return <div className="analytics-tab-loading" aria-label="Φόρτωση παραγγελιών ανά ώρα">Φόρτωση...</div>;
    }
    if (ordersByHourError) {
      return (
        <div className="analytics-tab-feedback">
          <div className="alert alert-error">⚠️ {ordersByHourError}</div>
          <button className="analytics-retry-btn" onClick={loadOrdersByHour}>Επανάληψη</button>
        </div>
      );
    }
    if (!ordersByHourData.length) {
      return <div className="analytics-tab-empty">Δεν υπάρχουν δεδομένα παραγγελιών ανά ώρα για την επιλεγμένη περίοδο.</div>;
    }

    return (
      <div className="analytics-chart-wrap" aria-label="Γράφημα παραγγελιών ανά ώρα">
        <ResponsiveContainer width="100%" height={300}>
          <LineChart
            data={ordersByHourData.map((r) => ({ hour: r.hour, orders: r.orders_count }))}
            margin={{ top: 16, right: 24, left: 8, bottom: 24 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis dataKey="hour" tick={{ fontSize: 12 }} />
            <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
            <Tooltip formatter={(v) => [v, 'Παραγγελίες']} />
            <Line
              type="monotone"
              dataKey="orders"
              stroke="#667eea"
              strokeWidth={2}
              dot={{ r: 4, fill: '#667eea' }}
              activeDot={{ r: 6 }}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    );
  };

  const renderLowRotationItems = () => {
    if (lowRotationItemsLoading) {
      return <div className="analytics-tab-loading" aria-label="Φόρτωση ειδών χαμηλής κυκλοφορίας">Φόρτωση...</div>;
    }
    if (lowRotationItemsError) {
      return (
        <div className="analytics-tab-feedback">
          <div className="alert alert-error">⚠️ {lowRotationItemsError}</div>
          <button className="analytics-retry-btn" onClick={loadLowRotationItems}>Επανάληψη</button>
        </div>
      );
    }
    if (!lowRotationItemsData.length) {
      return <div className="analytics-tab-empty">Δεν υπάρχουν είδη χαμηλής ζήτησης για την επιλεγμένη περίοδο.</div>;
    }

    return (
      <div className="analytics-chart-wrap" aria-label="Γράφημα ειδών χαμηλής ζήτησης">
        <ResponsiveContainer width="100%" height={360}>
          <BarChart
            data={lowRotationItemsData.map((r) => ({ item: r.item_name, qty: Number(r.qty_sold) }))}
            layout="vertical"
            margin={{ top: 12, right: 24, left: 24, bottom: 12 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} />
            <YAxis dataKey="item" type="category" width={120} tick={{ fontSize: 11 }} />
            <Tooltip formatter={(v) => [v, 'Πωλήσεις']} />
            <Bar dataKey="qty" fill="#f59e0b" radius={[0, 4, 4, 0]} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    );
  };

  const handleDateFromChange = (value) => {
    setFromDate(value);
    if (value > toDate) {
      setToDate(value);
    }
  };

  const handleDateToChange = (value) => {
    setToDate(value);
    if (value < fromDate) {
      setFromDate(value);
    }
  };

  const refreshActiveTab = () => {
    if (activeTab === 'overview') {
      loadSummary(fromDate, toDate);
      return;
    }
    if (activeTab === 'revenue-per-day') {
      loadRevenuePerDay(fromDate, toDate);
      return;
    }
    if (activeTab === 'revenue-per-workstation') {
      loadRevenuePerWorkstation(fromDate, toDate);
      return;
    }
    if (activeTab === 'orders-by-hour') {
      loadOrdersByHour(fromDate, toDate);
      return;
    }
    if (activeTab === 'low-rotation-items') {
      loadLowRotationItems(fromDate, toDate);
    }
  };

  return (
    <div className="analytics-section">
      <h2 className="analytics-title">📊 Ημερήσια Επισκόπηση</h2>

      <div className="analytics-controls">
        <div className="analytics-date-group">
          <label htmlFor="analytics-from">Από</label>
          <input
            id="analytics-from"
            type="date"
            value={fromDate}
            onChange={(e) => handleDateFromChange(e.target.value)}
          />
        </div>
        <div className="analytics-date-group">
          <label htmlFor="analytics-to">Έως</label>
          <input
            id="analytics-to"
            type="date"
            value={toDate}
            onChange={(e) => handleDateToChange(e.target.value)}
          />
        </div>
        <button className="analytics-refresh-btn" onClick={refreshActiveTab}>
          Ανανέωση
        </button>
      </div>

      <div className="analytics-tabs" role="tablist" aria-label="Καρτέλες στατιστικών">
        <button
          className={`analytics-tab ${activeTab === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveTab('overview')}
          role="tab"
          aria-selected={activeTab === 'overview'}
        >
          Επισκόπηση
        </button>
        <button
          className={`analytics-tab ${activeTab === 'revenue-per-day' ? 'active' : ''}`}
          onClick={() => setActiveTab('revenue-per-day')}
          role="tab"
          aria-selected={activeTab === 'revenue-per-day'}
        >
          Έσοδα ανά μέρα
        </button>
        <button
          className={`analytics-tab ${activeTab === 'revenue-per-workstation' ? 'active' : ''}`}
          onClick={() => setActiveTab('revenue-per-workstation')}
          role="tab"
          aria-selected={activeTab === 'revenue-per-workstation'}
        >
          Έσοδα ανά πόστο
        </button>
        <button
          className={`analytics-tab ${activeTab === 'orders-by-hour' ? 'active' : ''}`}
          onClick={() => setActiveTab('orders-by-hour')}
          role="tab"
          aria-selected={activeTab === 'orders-by-hour'}
        >
          Παραγγελίες ανά ώρα
        </button>
        <button
          className={`analytics-tab ${activeTab === 'low-rotation-items' ? 'active' : ''}`}
          onClick={() => setActiveTab('low-rotation-items')}
          role="tab"
          aria-selected={activeTab === 'low-rotation-items'}
        >
          Είδη χαμηλής ζήτησης
        </button>
      </div>

      <div className="analytics-tab-content">
        {activeTab === 'overview' && renderOverview()}
        {activeTab === 'revenue-per-day' && renderRevenuePerDay()}
        {activeTab === 'revenue-per-workstation' && renderRevenuePerWorkstation()}
        {activeTab === 'orders-by-hour' && renderOrdersByHour()}
        {activeTab === 'low-rotation-items' && renderLowRotationItems()}
      </div>
    </div>
  );
}

export default Analytics;

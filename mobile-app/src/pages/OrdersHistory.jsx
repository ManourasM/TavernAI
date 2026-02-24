// src/pages/OrdersHistory.jsx
// Page for viewing order history with filters and pagination

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { fetchOrderHistory, formatDate, formatCurrency } from '../services/historyService';
import './OrdersHistory.css';

export default function OrdersHistory() {
  const navigate = useNavigate();
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState({
    from: '',
    to: '',
    table: ''
  });
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 20;

  // Load history on mount and when filters change
  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const data = await fetchOrderHistory(filters);
      console.log('[OrdersHistory] Received data:', data);
      
      // Ensure we always have an array
      const historyArray = Array.isArray(data) ? data : (data?.items || data?.receipts || []);
      console.log('[OrdersHistory] Setting history array:', historyArray);
      
      setHistory(historyArray);
      setCurrentPage(1); // Reset to first page on new search
    } catch (err) {
      console.error('[OrdersHistory] Failed to load history:', err);
      setError(err.message || 'Αποτυχία φόρτωσης ιστορικού');
      setHistory([]); // Set empty array on error
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (field, value) => {
    setFilters(prev => ({ ...prev, [field]: value }));
  };

  const handleSearch = (e) => {
    e.preventDefault();
    loadHistory();
  };

  const handleClearFilters = () => {
    setFilters({ from: '', to: '', table: '' });
    // Load all history
    setTimeout(() => loadHistory(), 0);
  };

  const handleViewReceipt = (receiptId) => {
    navigate(`/receipt/${receiptId}`);
  };

  // Ensure history is always an array for pagination
  const historyArray = Array.isArray(history) ? history : [];

  // Pagination logic
  const totalPages = Math.ceil(historyArray.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const currentItems = historyArray.slice(startIndex, endIndex);

  const goToPage = (page) => {
    if (page >= 1 && page <= totalPages) {
      setCurrentPage(page);
    }
  };

  return (
    <div className="orders-history-page">
      <div className="history-header">
        <button className="back-button" onClick={() => navigate(-1)}>
          ← Πίσω
        </button>
        <h1>Ιστορικό Παραγγελιών</h1>
      </div>

      {/* Filters */}
      <form className="history-filters" onSubmit={handleSearch}>
        <div className="filter-group">
          <label htmlFor="from-date">Από:</label>
          <input
            id="from-date"
            type="date"
            value={filters.from}
            onChange={(e) => handleFilterChange('from', e.target.value)}
          />
        </div>

        <div className="filter-group">
          <label htmlFor="to-date">Έως:</label>
          <input
            id="to-date"
            type="date"
            value={filters.to}
            onChange={(e) => handleFilterChange('to', e.target.value)}
          />
        </div>

        <div className="filter-group">
          <label htmlFor="table-filter">Τραπέζι:</label>
          <input
            id="table-filter"
            type="number"
            min="1"
            placeholder="Όλα"
            value={filters.table}
            onChange={(e) => handleFilterChange('table', e.target.value)}
          />
        </div>

        <div className="filter-actions">
          <button type="submit" className="search-button" disabled={loading}>
            {loading ? 'Φόρτωση...' : 'Αναζήτηση'}
          </button>
          <button type="button" className="clear-button" onClick={handleClearFilters}>
            Καθαρισμός
          </button>
        </div>
      </form>

      {/* Error display */}
      {error && (
        <div className="history-error">
          ❌ {error}
        </div>
      )}

      {/* History list */}
      {loading ? (
        <div className="history-loading">Φόρτωση ιστορικού...</div>
      ) : (
        <>
          {currentItems.length === 0 ? (
            <div className="history-empty">
              Δεν βρέθηκαν παραγγελίες
            </div>
          ) : (
            <>
              <div className="history-list">
                {currentItems.map((receipt) => (
                  <div 
                    key={receipt.id} 
                    className="history-item"
                    onClick={() => handleViewReceipt(receipt.id)}
                  >
                    <div className="receipt-header">
                      <span className="receipt-table">Τραπέζι {receipt.table}</span>
                      <span className="receipt-date">{formatDate(receipt.closed_at || receipt.created_at)}</span>
                    </div>
                    <div className="receipt-details">
                      <span className="receipt-items">
                        {receipt.items?.length || 0} είδη
                      </span>
                      <span className="receipt-total">
                        {formatCurrency(receipt.total || 0)}
                      </span>
                    </div>
                    <div className="receipt-id">
                      Απόδειξη #{String(receipt.id).slice(0, 8)}
                    </div>
                  </div>
                ))}
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="history-pagination">
                  <button 
                    className="page-button"
                    onClick={() => goToPage(currentPage - 1)}
                    disabled={currentPage === 1}
                  >
                    ← Προηγούμενη
                  </button>
                  
                  <span className="page-info">
                    Σελίδα {currentPage} από {totalPages}
                  </span>
                  
                  <button 
                    className="page-button"
                    onClick={() => goToPage(currentPage + 1)}
                    disabled={currentPage === totalPages}
                  >
                    Επόμενη →
                  </button>
                </div>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}

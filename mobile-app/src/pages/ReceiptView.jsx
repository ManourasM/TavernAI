// src/pages/ReceiptView.jsx
// Page for viewing and printing individual receipts

import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { fetchReceipt, formatDate, formatCurrency } from '../services/historyService';
import { getProfile } from '../services/restaurantService';
import './ReceiptView.css';

export default function ReceiptView() {
  const { receiptId } = useParams();
  const navigate = useNavigate();
  const printAreaRef = useRef(null);
  
  const [receipt, setReceipt] = useState(null);
  const [restaurant, setRestaurant] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadReceiptAndProfile();
  }, [receiptId]);

  const loadReceiptAndProfile = async () => {
    setLoading(true);
    setError(null);

    try {
      // Load receipt
      const receiptData = await fetchReceipt(receiptId);
      setReceipt(receiptData);
      
      // Use restaurant data from receipt if available, otherwise fetch separately
      if (receiptData.restaurant) {
        console.log('[ReceiptView] Using restaurant data from receipt:', receiptData.restaurant);
        setRestaurant(receiptData.restaurant);
      } else {
        // Fallback: fetch restaurant profile separately
        console.log('[ReceiptView] Fetching restaurant profile...');
        const profileData = await getProfile();
        setRestaurant({
          name: profileData.name,
          phone: profileData.phone,
          address: profileData.address,
        });
      }
    } catch (err) {
      console.error('[ReceiptView] Failed to load receipt/profile:', err);
      setError(err.message || 'Αποτυχία φόρτωσης απόδειξής');
    } finally {
      setLoading(false);
    }
  };

  const handlePrint = () => {
    window.print();
  };

  if (loading) {
    return (
      <div className="receipt-view-page">
        <div className="receipt-loading">Φόρτωση απόδειξης...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="receipt-view-page">
        <div className="receipt-error">
          ❌ {error}
        </div>
        <button className="back-button" onClick={() => navigate(-1)}>
          ← Πίσω στο Ιστορικό
        </button>
      </div>
    );
  }

  if (!receipt) {
    return (
      <div className="receipt-view-page">
        <div className="receipt-error">Η απόδειξη δεν βρέθηκε</div>
        <button className="back-button" onClick={() => navigate(-1)}>
          ← Πίσω στο Ιστορικό
        </button>
      </div>
    );
  }

  // Calculate totals
  const total = receipt.items?.reduce((sum, item) => {
    const lineTotal = item.line_total || ((item.unit_price || item.price || 0) * (item.quantity || 1));
    return sum + lineTotal;
  }, 0) || 0;

  return (
    <div className="receipt-view-page">
      {/* Print controls (hidden when printing) */}
      <div className="receipt-controls no-print">
        <button className="back-button" onClick={() => navigate(-1)}>
          ← Πίσω στο Ιστορικό
        </button>
        <button className="print-button" onClick={handlePrint}>
          🖨️ Εκτύπωση
        </button>
      </div>

      {/* Printable receipt content */}
      <div className="receipt-content" ref={printAreaRef}>
        {/* Restaurant header */}
        <div className="receipt-restaurant">
          <h1>{restaurant?.name || 'ΤΑΒΕΡΝΑ'}</h1>
          <p className="restaurant-details">
            {restaurant?.address && (
              <>
                {restaurant.address}<br />
              </>
            )}
            {restaurant?.phone && (
              <>
                Τηλ: {restaurant.phone}<br />
              </>
            )}
            {restaurant?.extra_details?.afm && (
              <>
                ΑΦΜ: {restaurant.extra_details.afm}<br />
              </>
            )}
          </p>
        </div>

        {/* Receipt info */}
        <div className="receipt-info">
          <div className="receipt-row">
            <span className="label">Απόδειξη:</span>
            <span className="value">#{String(receipt.id).slice(0, 12)}</span>
          </div>
          <div className="receipt-row">
            <span className="label">Τραπέζι:</span>
            <span className="value">{receipt.table}</span>
          </div>
          <div className="receipt-row">
            <span className="label">Ημερομηνία:</span>
            <span className="value">{formatDate(receipt.closed_at || receipt.created_at)}</span>
          </div>
          {receipt.waiter && (
            <div className="receipt-row">
              <span className="label">Σερβιτόρος:</span>
              <span className="value">{receipt.waiter}</span>
            </div>
          )}
        </div>

        <hr className="receipt-divider" />

        {/* Items table */}
        <table className="receipt-items-table">
          <thead>
            <tr>
              <th className="item-name-col">Είδος</th>
              <th className="item-qty-col">Ποσ.</th>
              <th className="item-price-col">Τιμή</th>
              <th className="item-total-col">Σύνολο</th>
            </tr>
          </thead>
          <tbody>
            {receipt.items?.map((item, idx) => {
              const itemPrice = item.unit_price || item.price || 0;
              const itemQty = item.quantity || 1;
              const itemTotal = item.line_total || (itemPrice * itemQty);
              
              return (
                <tr key={idx}>
                  <td className="item-name">
                    {item.menu_name || item.text || item.name || 'Άγνωστο είδος'}
                  </td>
                  <td className="item-qty">{itemQty}</td>
                  <td className="item-price">{formatCurrency(itemPrice)}</td>
                  <td className="item-total">{formatCurrency(itemTotal)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>

        <hr className="receipt-divider" />

        {/* Totals */}
        <div className="receipt-totals">
          <div className="receipt-row total-row">
            <span className="label">ΣΥΝΟΛΟ:</span>
            <span className="value">{formatCurrency(total)}</span>
          </div>
        </div>

        {/* Footer */}
        <div className="receipt-footer">
          <p>Ευχαριστούμε για την επίσκεψή σας!</p>
          <p className="receipt-footer-small">
            Παρακαλούμε ελέγξτε την απόδειξή σας πριν αποχωρήσετε.
          </p>
        </div>
      </div>
    </div>
  );
}

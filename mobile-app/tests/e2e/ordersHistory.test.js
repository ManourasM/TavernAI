// tests/e2e/ordersHistory.test.js
// E2E tests for order history and receipt viewing

import { describe, it, expect, beforeAll, afterAll, beforeEach } from 'vitest';
import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import OrdersHistory from '../../src/pages/OrdersHistory';
import ReceiptView from '../../src/pages/ReceiptView';

// Mock data
const mockHistoryData = [
  {
    id: 'receipt-001',
    table: 1,
    items: [
      { id: 'item-1', name: 'Μουσακάς', price: 12.00, quantity: 2, menu_name: 'Μουσακάς' },
      { id: 'item-2', name: 'Σαλάτα', price: 5.00, quantity: 1, menu_name: 'Χωριάτικη σαλάτα' }
    ],
    total: 29.00,
    closed_at: '2026-02-23T12:30:00Z',
    created_at: '2026-02-23T12:00:00Z'
  },
  {
    id: 'receipt-002',
    table: 2,
    items: [
      { id: 'item-3', name: 'Σουβλάκι', price: 8.50, quantity: 3, menu_name: 'Σουβλάκι χοιρινό' }
    ],
    total: 25.50,
    closed_at: '2026-02-23T13:00:00Z',
    created_at: '2026-02-23T12:45:00Z'
  },
  {
    id: 'receipt-003',
    table: 3,
    items: [
      { id: 'item-4', name: 'Παϊδάκια', price: 15.00, quantity: 1, menu_name: 'Αρνίσια παϊδάκια' },
      { id: 'item-5', name: 'Μύθος', price: 4.00, quantity: 2, menu_name: 'Μύθος μπύρα' }
    ],
    total: 23.00,
    closed_at: '2026-02-22T19:30:00Z',
    created_at: '2026-02-22T19:00:00Z'
  }
];

const mockReceiptData = {
  id: 'receipt-001',
  table: 1,
  items: [
    { id: 'item-1', name: 'Μουσακάς', price: 12.00, quantity: 2, menu_name: 'Μουσακάς', text: '2 μουσακας' },
    { id: 'item-2', name: 'Σαλάτα', price: 5.00, quantity: 1, menu_name: 'Χωριάτικη σαλάτα', text: '1 σαλατα' }
  ],
  total: 29.00,
  closed_at: '2026-02-23T12:30:00Z',
  created_at: '2026-02-23T12:00:00Z',
  waiter: 'Γιώργος'
};

// Setup MSW server for API mocking
const server = setupServer(
  // Mock config endpoint
  http.get('*/config', () => {
    return HttpResponse.json({
      backend_base: 'http://localhost:8000',
      ws_base: 'ws://localhost:8000',
      backend_port: 8000
    });
  }),

  // Mock history endpoint
  http.get('*/api/orders/history', ({ request }) => {
    const url = new URL(request.url);
    const table = url.searchParams.get('table');
    const from = url.searchParams.get('from');
    const to = url.searchParams.get('to');

    let filteredData = [...mockHistoryData];

    if (table) {
      filteredData = filteredData.filter(r => r.table === parseInt(table));
    }

    if (from) {
      filteredData = filteredData.filter(r => new Date(r.closed_at) >= new Date(from));
    }

    if (to) {
      const toDate = new Date(to);
      toDate.setHours(23, 59, 59, 999);
      filteredData = filteredData.filter(r => new Date(r.closed_at) <= toDate);
    }

    return HttpResponse.json(filteredData);
  }),

  // Mock single receipt endpoint
  http.get('*/api/orders/history/:receiptId', ({ params }) => {
    const { receiptId } = params;
    
    if (receiptId === 'receipt-001') {
      return HttpResponse.json(mockReceiptData);
    }
    
    return new HttpResponse(null, { status: 404 });
  })
);

// Mock router navigation
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => ({ receiptId: 'receipt-001' })
  };
});

describe('Orders History E2E Tests', () => {
  beforeAll(() => {
    server.listen();
  });

  afterAll(() => {
    server.close();
  });

  beforeEach(() => {
    server.resetHandlers();
    mockNavigate.mockClear();
  });

  describe('OrdersHistory Page', () => {
    it('should render history page with data', async () => {
      render(
        <BrowserRouter>
          <OrdersHistory />
        </BrowserRouter>
      );

      // Check for page title
      expect(screen.getByText('Ιστορικό Παραγγελιών')).toBeInTheDocument();

      // Wait for data to load
      await waitFor(() => {
        expect(screen.getByText('Τραπέζι 1')).toBeInTheDocument();
      });

      // Check that all receipts are displayed
      expect(screen.getByText('Τραπέζι 1')).toBeInTheDocument();
      expect(screen.getByText('Τραπέζι 2')).toBeInTheDocument();
      expect(screen.getByText('Τραπέζι 3')).toBeInTheDocument();
    });

    it('should filter history by table number', async () => {
      render(
        <BrowserRouter>
          <OrdersHistory />
        </BrowserRouter>
      );

      // Wait for initial load
      await waitFor(() => {
        expect(screen.getByText('Τραπέζι 1')).toBeInTheDocument();
      });

      // Find and fill table filter
      const tableInput = screen.getByLabelText('Τραπέζι:');
      fireEvent.change(tableInput, { target: { value: '1' } });

      // Submit search
      const searchButton = screen.getByText('Αναζήτηση');
      fireEvent.click(searchButton);

      // Wait for filtered results
      await waitFor(() => {
        expect(screen.getByText('Τραπέζι 1')).toBeInTheDocument();
        expect(screen.queryByText('Τραπέζι 2')).not.toBeInTheDocument();
      });
    });

    it('should filter history by date range', async () => {
      render(
        <BrowserRouter>
          <OrdersHistory />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('Τραπέζι 1')).toBeInTheDocument();
      });

      // Set date filters
      const fromInput = screen.getByLabelText('Από:');
      const toInput = screen.getByLabelText('Έως:');
      
      fireEvent.change(fromInput, { target: { value: '2026-02-23' } });
      fireEvent.change(toInput, { target: { value: '2026-02-23' } });

      // Submit search
      const searchButton = screen.getByText('Αναζήτηση');
      fireEvent.click(searchButton);

      // Should only show receipts from Feb 23
      await waitFor(() => {
        expect(screen.getByText('Τραπέζι 1')).toBeInTheDocument();
        expect(screen.getByText('Τραπέζι 2')).toBeInTheDocument();
        expect(screen.queryByText('Τραπέζι 3')).not.toBeInTheDocument();
      });
    });

    it('should clear filters', async () => {
      render(
        <BrowserRouter>
          <OrdersHistory />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('Τραπέζι 1')).toBeInTheDocument();
      });

      // Set a filter
      const tableInput = screen.getByLabelText('Τραπέζι:');
      fireEvent.change(tableInput, { target: { value: '1' } });

      // Clear filters
      const clearButton = screen.getByText('Καθαρισμός');
      fireEvent.click(clearButton);

      // Input should be empty
      expect(tableInput.value).toBe('');
    });

    it('should navigate to receipt view on click', async () => {
      render(
        <BrowserRouter>
          <OrdersHistory />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('Τραπέζι 1')).toBeInTheDocument();
      });

      // Click on first receipt
      const firstReceipt = screen.getByText('Τραπέζι 1').closest('.history-item');
      fireEvent.click(firstReceipt);

      // Should navigate to receipt view
      expect(mockNavigate).toHaveBeenCalledWith('/receipt/receipt-001');
    });

    it('should show empty state when no receipts found', async () => {
      // Override handler to return empty array
      server.use(
        http.get('*/api/orders/history', () => {
          return HttpResponse.json([]);
        })
      );

      render(
        <BrowserRouter>
          <OrdersHistory />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('Δεν βρέθηκαν παραγγελίες')).toBeInTheDocument();
      });
    });
  });

  describe('ReceiptView Page', () => {
    it('should render receipt with all details', async () => {
      render(
        <BrowserRouter>
          <ReceiptView />
        </BrowserRouter>
      );

      // Wait for data to load
      await waitFor(() => {
        expect(screen.getByText('ΤΑΒΕΡΝΑ')).toBeInTheDocument();
      });

      // Check receipt header
      expect(screen.getByText(/Τραπέζι:/)).toBeInTheDocument();
      expect(screen.getByText('1')).toBeInTheDocument();
      expect(screen.getByText(/Σερβιτόρος:/)).toBeInTheDocument();
      expect(screen.getByText('Γιώργος')).toBeInTheDocument();

      // Check items
      expect(screen.getByText('Μουσακάς')).toBeInTheDocument();
      expect(screen.getByText('Χωριάτικη σαλάτα')).toBeInTheDocument();

      // Check quantities and prices
      expect(screen.getByText('2')).toBeInTheDocument(); // quantity
      expect(screen.getByText('1')).toBeInTheDocument(); // quantity

      // Check totals section exists
      expect(screen.getByText(/Υποσύνολο:/)).toBeInTheDocument();
      expect(screen.getByText(/ΦΠΑ/)).toBeInTheDocument();
      expect(screen.getByText(/ΣΥΝΟΛΟ:/)).toBeInTheDocument();
    });

    it('should have print button', async () => {
      render(
        <BrowserRouter>
          <ReceiptView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('ΤΑΒΕΡΝΑ')).toBeInTheDocument();
      });

      // Check for print button
      const printButton = screen.getByText(/Εκτύπωση/);
      expect(printButton).toBeInTheDocument();
    });

    it('should trigger print when print button clicked', async () => {
      // Mock window.print
      const mockPrint = vi.fn();
      global.window.print = mockPrint;

      render(
        <BrowserRouter>
          <ReceiptView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('ΤΑΒΕΡΝΑ')).toBeInTheDocument();
      });

      // Click print button
      const printButton = screen.getByText(/Εκτύπωση/);
      fireEvent.click(printButton);

      // Verify print was called
      expect(mockPrint).toHaveBeenCalled();
    });

    it('should navigate back to history on back button', async () => {
      render(
        <BrowserRouter>
          <ReceiptView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('ΤΑΒΕΡΝΑ')).toBeInTheDocument();
      });

      // Click back button
      const backButton = screen.getByText(/Πίσω στο Ιστορικό/);
      fireEvent.click(backButton);

      // Should navigate back
      expect(mockNavigate).toHaveBeenCalledWith(-1);
    });

    it('should show error for non-existent receipt', async () => {
      // Mock useParams to return invalid ID
      vi.mock('react-router-dom', async () => {
        const actual = await vi.importActual('react-router-dom');
        return {
          ...actual,
          useNavigate: () => mockNavigate,
          useParams: () => ({ receiptId: 'invalid-receipt' })
        };
      });

      render(
        <BrowserRouter>
          <ReceiptView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText(/Αποτυχία φόρτωσης/)).toBeInTheDocument();
      });
    });
  });

  describe('Integration: History to Receipt Flow', () => {
    it('should navigate from history list to receipt view', async () => {
      // First render history
      const { rerender } = render(
        <BrowserRouter>
          <OrdersHistory />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('Τραπέζι 1')).toBeInTheDocument();
      });

      // Click on receipt
      const receipt = screen.getByText('Τραπέζι 1').closest('.history-item');
      fireEvent.click(receipt);

      // Verify navigation was called
      expect(mockNavigate).toHaveBeenCalledWith('/receipt/receipt-001');

      // Simulate navigation by rendering receipt view
      rerender(
        <BrowserRouter>
          <ReceiptView />
        </BrowserRouter>
      );

      // Verify receipt details are shown
      await waitFor(() => {
        expect(screen.getByText('ΤΑΒΕΡΝΑ')).toBeInTheDocument();
        expect(screen.getByText('Μουσακάς')).toBeInTheDocument();
      });
    });
  });
});

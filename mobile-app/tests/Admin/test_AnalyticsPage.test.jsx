// @vitest-environment jsdom
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, fireEvent, act, cleanup, waitFor } from '@testing-library/react';
import Analytics from '../../src/pages/Admin/Analytics';
import * as analyticsService from '../../src/services/analyticsService';

function todayIsoDate() {
  const now = new Date();
  const local = new Date(now.getTime() - now.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 10);
}

// Mock the analytics service
vi.mock('../../src/services/analyticsService', () => ({
  getAnalyticsSummary: vi.fn(),
  getLowRotationItems: vi.fn(),
  getOrdersByHour: vi.fn(),
  getRevenuePerDay: vi.fn(),
  getRevenuePerWorkstation: vi.fn(),
}));

describe('Analytics Admin Page', () => {
  const mockSummary = {
    today_revenue: 125.50,
    revenue_change_vs_previous_day: 12.5,
    orders_count: 7,
    average_ticket_size: 17.93,
    top_items_today: [
      { name: 'Μπρίζολα', qty: 4, revenue_cents: 4800 },
      { name: 'Σαλάτα', qty: 3, revenue_cents: 1800 },
      { name: 'Κρασί', qty: 2, revenue_cents: 1400 },
    ],
    busiest_workstation: 'grill',
    peak_hour: '13:00',
  };

  beforeEach(() => {
    vi.clearAllMocks();
    analyticsService.getAnalyticsSummary.mockResolvedValue(mockSummary);
    analyticsService.getRevenuePerDay.mockResolvedValue([
      { date: '2026-03-24', revenue: 120.5 },
      { date: '2026-03-25', revenue: 90.0 },
    ]);
    analyticsService.getRevenuePerWorkstation.mockResolvedValue([
      { workstation: 'grill', revenue: 130.0 },
      { workstation: 'kitchen', revenue: 80.5 },
    ]);
    analyticsService.getOrdersByHour.mockResolvedValue([
      { hour: '00:00', orders_count: 0 },
      { hour: '11:00', orders_count: 3 },
      { hour: '12:00', orders_count: 0 },
    ]);
    analyticsService.getLowRotationItems.mockResolvedValue([
      { item_name: 'Λεμονάδα', qty_sold: 1 },
      { item_name: 'Σουβλάκι', qty_sold: 2 },
    ]);
  });

  afterEach(() => {
    cleanup();
  });

  it('renders KPI cards with correct data', async () => {
    await act(async () => { render(<Analytics />); });

    expect(screen.getByText('Έσοδα Σήμερα')).toBeTruthy();
    expect(screen.getByText('€125.50')).toBeTruthy();
    expect(screen.getByText('Μέση Αξία Παραγγελίας')).toBeTruthy();
    expect(screen.getByText('€17.93')).toBeTruthy();
    expect(screen.getByText('Αριθμός Παραγγελιών')).toBeTruthy();
    expect(screen.getByText('7')).toBeTruthy();
    expect(screen.getByText('Πιο Πολυάσχολο Πόστο')).toBeTruthy();
    expect(screen.getByText('grill')).toBeTruthy();
    expect(screen.getByText('Ώρα Αιχμής')).toBeTruthy();
    expect(screen.getByText('13:00')).toBeTruthy();
  });

  it('shows skeleton loading state before data arrives', () => {
    // Never resolves so component stays in skeleton/loading state
    analyticsService.getAnalyticsSummary.mockImplementationOnce(
      () => new Promise(() => {/* never resolves */})
    );

    render(<Analytics />);

    // Data labels must not be visible while loading
    expect(screen.queryByText('Έσοδα Σήμερα')).toBeNull();
    // Loading skeleton grid must be present (aria-label="Φόρτωση")
    expect(screen.queryByLabelText('Φόρτωση')).toBeTruthy();
  });

  it('shows Greek empty state when orders_count is 0', async () => {
    analyticsService.getAnalyticsSummary.mockResolvedValueOnce({
      ...mockSummary,
      orders_count: 0,
      today_revenue: 0,
      average_ticket_size: 0,
      top_items_today: [],
      busiest_workstation: null,
      peak_hour: null,
    });

    await act(async () => { render(<Analytics />); });

    expect(
      screen.getByText('Δεν υπάρχουν δεδομένα παραγγελιών για σήμερα.')
    ).toBeTruthy();
      expect(screen.getByText(/Κορυφαία 3 Προϊόντα/)).toBeTruthy();
  });

  it('renders top 3 items list correctly', async () => {
    await act(async () => { render(<Analytics />); });

    expect(screen.getByText('Μπρίζολα')).toBeTruthy();
    expect(screen.getByText('Σαλάτα')).toBeTruthy();
    expect(screen.getByText('Κρασί')).toBeTruthy();
    // Each qty formatted with suffix
    expect(screen.getAllByText(/τεμ\./)).toHaveLength(3);
  });

  it('shows revenue change badge when non-zero', async () => {
    await act(async () => { render(<Analytics />); });

    expect(screen.getByText('▲12.5%')).toBeTruthy();
  });

  it('hides revenue change badge when change is 0', async () => {
    analyticsService.getAnalyticsSummary.mockResolvedValueOnce({
      ...mockSummary,
      revenue_change_vs_previous_day: 0,
    });

    await act(async () => { render(<Analytics />); });

    expect(screen.getByText('Έσοδα Σήμερα')).toBeTruthy();
    expect(screen.queryByText(/▲|▼/)).toBeNull();
  });

  it('shows negative revenue change with down arrow', async () => {
    analyticsService.getAnalyticsSummary.mockResolvedValueOnce({
      ...mockSummary,
      revenue_change_vs_previous_day: -8.3,
    });

    await act(async () => { render(<Analytics />); });

    expect(screen.getByText('▼8.3%')).toBeTruthy();
  });

  it('shows error message when service call fails', async () => {
    analyticsService.getAnalyticsSummary.mockRejectedValueOnce(
      new Error('Αποτυχία φόρτωσης στατιστικών: 500')
    );

    await act(async () => { render(<Analytics />); });

    expect(screen.getByText(/Αποτυχία φόρτωσης στατιστικών: 500/)).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Επανάληψη' })).toBeTruthy();
  });

  it('switches to Revenue per day and loads rows', async () => {
    await act(async () => { render(<Analytics />); });

    await act(async () => {
      fireEvent.click(screen.getByRole('tab', { name: 'Έσοδα ανά μέρα' }));
    });

    expect(analyticsService.getRevenuePerDay).toHaveBeenCalledTimes(1);
    expect(screen.getByText('2026-03-24')).toBeTruthy();
    // value is in tooltip (not DOM) — verify the chart container rendered
    expect(screen.getByLabelText('Γράφημα εσόδων ανά μέρα')).toBeTruthy();
  });

  it('switches to Revenue per workstation and loads rows', async () => {
    await act(async () => { render(<Analytics />); });

    await act(async () => {
      fireEvent.click(screen.getByRole('tab', { name: 'Έσοδα ανά πόστο' }));
    });

    expect(analyticsService.getRevenuePerWorkstation).toHaveBeenCalledTimes(1);
    expect(screen.getAllByText('grill').length).toBeGreaterThan(0);
    expect(screen.getByLabelText('Γράφημα εσόδων ανά πόστο')).toBeTruthy();
  });

  it('does not refetch Revenue per day after initial load', async () => {
    await act(async () => { render(<Analytics />); });

    await act(async () => {
      fireEvent.click(screen.getByRole('tab', { name: 'Έσοδα ανά μέρα' }));
    });
    expect(analyticsService.getRevenuePerDay).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole('tab', { name: 'Επισκόπηση' }));
    fireEvent.click(screen.getByRole('tab', { name: 'Έσοδα ανά μέρα' }));

    expect(analyticsService.getRevenuePerDay).toHaveBeenCalledTimes(1);
  });

  it('shows empty state in Revenue per workstation when API returns no rows', async () => {
    analyticsService.getRevenuePerWorkstation.mockResolvedValueOnce([]);
    await act(async () => { render(<Analytics />); });

    await act(async () => {
      fireEvent.click(screen.getByRole('tab', { name: 'Έσοδα ανά πόστο' }));
    });

    expect(screen.getByText(/Δεν υπάρχουν δεδομένα εσόδων ανά πόστο/)).toBeTruthy();
  });

  it('switches to Orders by hour and loads rows', async () => {
    await act(async () => { render(<Analytics />); });

    await act(async () => {
      fireEvent.click(screen.getByRole('tab', { name: 'Παραγγελίες ανά ώρα' }));
    });

    expect(analyticsService.getOrdersByHour).toHaveBeenCalledTimes(1);
    expect(screen.getByText('11:00')).toBeTruthy();
    expect(screen.getByLabelText('Γράφημα παραγγελιών ανά ώρα')).toBeTruthy();
  });

  it('switches to Low rotation items and loads rows', async () => {
    await act(async () => { render(<Analytics />); });

    await act(async () => {
      fireEvent.click(screen.getByRole('tab', { name: 'Είδη χαμηλής ζήτησης' }));
    });

    expect(analyticsService.getLowRotationItems).toHaveBeenCalledTimes(1);
    expect(screen.getAllByText('Λεμονάδα').length).toBeGreaterThan(0);
    expect(screen.getByLabelText('Γράφημα ειδών χαμηλής ζήτησης')).toBeTruthy();
  });

  it('does not refetch Orders by hour after initial load', async () => {
    await act(async () => { render(<Analytics />); });

    await act(async () => {
      fireEvent.click(screen.getByRole('tab', { name: 'Παραγγελίες ανά ώρα' }));
    });
    expect(analyticsService.getOrdersByHour).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole('tab', { name: 'Επισκόπηση' }));
    fireEvent.click(screen.getByRole('tab', { name: 'Παραγγελίες ανά ώρα' }));

    expect(analyticsService.getOrdersByHour).toHaveBeenCalledTimes(1);
  });

  it('shows empty state in Low rotation items when API returns no rows', async () => {
    analyticsService.getLowRotationItems.mockResolvedValueOnce([]);
    await act(async () => { render(<Analytics />); });

    await act(async () => {
      fireEvent.click(screen.getByRole('tab', { name: 'Είδη χαμηλής ζήτησης' }));
    });

    expect(screen.getByText(/Δεν υπάρχουν είδη χαμηλής ζήτησης/)).toBeTruthy();
  });

  it('triggers new API calls when date range changes', async () => {
    await act(async () => { render(<Analytics />); });

    const fromInput = screen.getByLabelText('Από');
    const toInput = screen.getByLabelText('Έως');

    await act(async () => {
      fireEvent.change(fromInput, { target: { value: '2026-03-20' } });
    });
    await act(async () => {
      fireEvent.change(toInput, { target: { value: '2026-03-24' } });
    });

    await waitFor(() => {
      expect(analyticsService.getAnalyticsSummary).toHaveBeenCalled();
    });

    const calls = analyticsService.getAnalyticsSummary.mock.calls;
    expect(calls.length).toBeGreaterThan(1);
    expect(calls[calls.length - 1]).toEqual(['2026-03-20', '2026-03-24']);
  });

  it('refresh button refetches active tab data', async () => {
    await act(async () => { render(<Analytics />); });

    await act(async () => {
      fireEvent.click(screen.getByRole('tab', { name: 'Παραγγελίες ανά ώρα' }));
    });
    expect(analyticsService.getOrdersByHour).toHaveBeenCalledTimes(1);

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Ανανέωση' }));
    });
    expect(analyticsService.getOrdersByHour).toHaveBeenCalledTimes(2);
  });

  it('overview still loads correctly after filter changes', async () => {
    await act(async () => { render(<Analytics />); });

    await act(async () => {
      fireEvent.change(screen.getByLabelText('Από'), { target: { value: '2026-03-22' } });
    });
    await act(async () => {
      fireEvent.change(screen.getByLabelText('Έως'), { target: { value: '2026-03-24' } });
    });

    await waitFor(() => {
      expect(screen.getByText('Έσοδα Σήμερα')).toBeTruthy();
      expect(screen.getByText('€125.50')).toBeTruthy();
    });

    // Initial load uses today's range by default before updates
    expect(analyticsService.getAnalyticsSummary.mock.calls[0]).toEqual([
      todayIsoDate(),
      todayIsoDate(),
    ]);
  });
});

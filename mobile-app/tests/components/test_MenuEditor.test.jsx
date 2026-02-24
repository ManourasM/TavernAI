import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import MenuEditor from '../../src/components/MenuEditor';

// Mock the API module
vi.mock('../../src/services/api', () => ({
  getConfig: vi.fn(),
}));

// Mock the menu store
vi.mock('../../src/store/menuStore', () => ({
  default: vi.fn((selector) => {
    // Return a mock that returns empty endpoints array
    if (typeof selector === 'function') {
      return selector({ endpoints: [] });
    }
    return { endpoints: [] };
  }),
}));

describe('MenuEditor with Dynamic Categories', () => {
  const mockInitialMenu = [
    { id: 1, name: 'Greek Salad', price: 9.5, category: 'kitchen', unit: 'portion', hidden: false },
    { id: 2, name: 'Pork Chop', price: 15.0, category: 'grill', unit: 'portion', hidden: false },
    { id: 3, name: 'Mythos Beer', price: 4.0, category: 'drinks', unit: 'portion', hidden: false },
  ];

  const mockMenuResponse = {
    Salads: [
      { id: 'salads_01', name: 'Greek Salad', price: 9.5, category: 'kitchen' },
    ],
    Grill: [
      { id: 'grill_01', name: 'Pork Chop', price: 15.0, category: 'grill' },
    ],
    Drinks: [
      { id: 'drinks_01', name: 'Mythos Beer', price: 4.0, category: 'drinks' },
    ],
    available_categories: [
      { slug: 'kitchen', name: 'Kitchen' },
      { slug: 'grill', name: 'Grill' },
      { slug: 'drinks', name: 'Drinks Bar' },
    ],
  };

  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = vi.fn();
  });

  it('loads available categories from API on mount', async () => {
    const { getConfig } = require('../../src/services/api');
    getConfig.mockResolvedValue({ backend_base: 'http://localhost:8000' });

    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockMenuResponse,
    });

    const mockOnSave = vi.fn();
    const mockOnBack = vi.fn();

    render(
      <MenuEditor
        initialMenu={mockInitialMenu}
        onSave={mockOnSave}
        onBack={mockOnBack}
        loading={false}
      />
    );

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/menu',
        expect.objectContaining({ method: 'GET' })
      );
    });
  });

  it('displays available categories in dropdown when adding new item', async () => {
    const { getConfig } = require('../../src/services/api');
    getConfig.mockResolvedValue({ backend_base: 'http://localhost:8000' });

    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockMenuResponse,
    });

    const mockOnSave = vi.fn();
    const mockOnBack = vi.fn();

    render(
      <MenuEditor
        initialMenu={[]}
        onSave={mockOnSave}
        onBack={mockOnBack}
        loading={false}
      />
    );

    const addButton = await screen.findByText('+ Add');
    fireEvent.click(addButton);

    await waitFor(() => {
      const selects = screen.getAllByRole('combobox');
      expect(selects.length).toBeGreaterThan(0);
    });
  });

  it('detects legacy categories not in available_categories', async () => {
    const { getConfig } = require('../../src/services/api');
    getConfig.mockResolvedValue({ backend_base: 'http://localhost:8000' });

    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockMenuResponse,
    });

    const legacyMenu = [
      { id: 1, name: 'Old Item', price: 10, category: 'removed_station', unit: 'portion', hidden: false },
    ];

    const mockOnSave = vi.fn();
    const mockOnBack = vi.fn();

    render(
      <MenuEditor
        initialMenu={legacyMenu}
        onSave={mockOnSave}
        onBack={mockOnBack}
        loading={false}
      />
    );

    await waitFor(() => {
      // Should show warning for legacy category
      expect(screen.getByText(/Legacy category/)).toBeInTheDocument();
    });
  });

  it('displays warning when editing item with legacy category', async () => {
    const { getConfig } = require('../../src/services/api');
    getConfig.mockResolvedValue({ backend_base: 'http://localhost:8000' });

    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockMenuResponse,
    });

    const legacyMenu = [
      { id: 1, name: 'Old Item', price: 10, category: 'removed_station', unit: 'portion', hidden: false },
    ];

    const mockOnSave = vi.fn();
    const mockOnBack = vi.fn();

    render(
      <MenuEditor
        initialMenu={legacyMenu}
        onSave={mockOnSave}
        onBack={mockOnBack}
        loading={false}
      />
    );

    const editButton = await screen.findByRole('button', { name: /✎/ });
    fireEvent.click(editButton);

    await waitFor(() => {
      expect(
        screen.getByText(/This item uses category "removed_station" which is no longer available/)
      ).toBeInTheDocument();
    });
  });

  it('allows user to change legacy category to valid one', async () => {
    const { getConfig } = require('../../src/services/api');
    getConfig.mockResolvedValue({ backend_base: 'http://localhost:8000' });

    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockMenuResponse,
    });

    const legacyMenu = [
      { id: 1, name: 'Old Item', price: 10, category: 'removed_station', unit: 'portion', hidden: false },
    ];

    const mockOnSave = vi.fn();
    const mockOnBack = vi.fn();

    render(
      <MenuEditor
        initialMenu={legacyMenu}
        onSave={mockOnSave}
        onBack={mockOnBack}
        loading={false}
      />
    );

    const editButton = await screen.findByRole('button', { name: /✎/ });
    fireEvent.click(editButton);

    await waitFor(() => {
      const selects = screen.getAllByRole('combobox');
      expect(selects.length).toBeGreaterThan(0);
    });

    // Change to valid category (Grill)
    const categorySelect = screen.getAllByRole('combobox')[2]; // Category is usually 3rd select
    fireEvent.change(categorySelect, { target: { value: 'grill' } });

    const saveButton = screen.getByRole('button', { name: /✓ Save/ });
    fireEvent.click(saveButton);

    // Menu should be updated
    expect(mockOnSave).not.toHaveBeenCalled(); // Save menu not called yet, just save edit
  });

  it('calls onSave with updated menu when Save Menu button clicked', async () => {
    const { getConfig } = require('../../src/services/api');
    getConfig.mockResolvedValue({ backend_base: 'http://localhost:8000' });

    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockMenuResponse,
    });

    const mockOnSave = vi.fn();
    const mockOnBack = vi.fn();

    render(
      <MenuEditor
        initialMenu={mockInitialMenu}
        onSave={mockOnSave}
        onBack={mockOnBack}
        loading={false}
      />
    );

    const saveMenuButton = await screen.findByText(/Save Menu/);
    fireEvent.click(saveMenuButton);

    expect(mockOnSave).toHaveBeenCalledWith(mockInitialMenu);
  });

  it('shows fallback to endpoints when API fails', async () => {
    const { getConfig } = require('../../src/services/api');
    getConfig.mockResolvedValue({ backend_base: 'http://localhost:8000' });

    global.fetch.mockRejectedValueOnce(new Error('Network error'));

    const mockOnSave = vi.fn();
    const mockOnBack = vi.fn();

    render(
      <MenuEditor
        initialMenu={mockInitialMenu}
        onSave={mockOnSave}
        onBack={mockOnBack}
        loading={false}
      />
    );

    await waitFor(() => {
      // Should show warning about not being able to load categories
      expect(screen.getByText(/Could not load workstations/)).toBeInTheDocument();
    });
  });

  it('uses first available category as default for new item', async () => {
    const { getConfig } = require('../../src/services/api');
    getConfig.mockResolvedValue({ backend_base: 'http://localhost:8000' });

    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockMenuResponse,
    });

    const mockOnSave = vi.fn();
    const mockOnBack = vi.fn();

    render(
      <MenuEditor
        initialMenu={[]}
        onSave={mockOnSave}
        onBack={mockOnBack}
        loading={false}
      />
    );

    const addButton = await screen.findByText('+ Add');
    fireEvent.click(addButton);

    await waitFor(() => {
      const selects = screen.getAllByRole('combobox');
      // Category select should have first category (kitchen) selected
      expect(selects[2]).toHaveValue('kitchen');
    });
  });

  it('displays category display names not slugs', async () => {
    const { getConfig } = require('../../src/services/api');
    getConfig.mockResolvedValue({ backend_base: 'http://localhost:8000' });

    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockMenuResponse,
    });

    const mockOnSave = vi.fn();
    const mockOnBack = vi.fn();

    render(
      <MenuEditor
        initialMenu={mockInitialMenu}
        onSave={mockOnSave}
        onBack={mockOnBack}
        loading={false}
      />
    );

    // Should display "Kitchen" not "kitchen"
    await waitFor(() => {
      components.forEach((item) => {
        if (item.category === 'kitchen') {
          // In display mode, should show "Kitchen" name
          const items = screen.getAllByText(/Kitchen|Grill|Drinks Bar/);
          expect(items.length).toBeGreaterThan(0);
        }
      });
    });
  });

  it('handles empty available_categories gracefully', async () => {
    const { getConfig } = require('../../src/services/api');
    getConfig.mockResolvedValue({ backend_base: 'http://localhost:8000' });

    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        Salads: [],
        available_categories: [],
      }),
    });

    const mockOnSave = vi.fn();
    const mockOnBack = vi.fn();

    render(
      <MenuEditor
        initialMenu={[]}
        onSave={mockOnSave}
        onBack={mockOnBack}
        loading={false}
      />
    );

    const addButton = await screen.findByText('+ Add');
    fireEvent.click(addButton);

    await waitFor(() => {
      // Should use fallback default
      expect(screen.getByText('New Item')).toBeInTheDocument();
    });
  });
});

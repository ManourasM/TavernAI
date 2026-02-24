import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import MenuEditor from '../../src/pages/Admin/MenuEditor';
import * as menuService from '../../src/services/menuService';
import useMenuStore from '../../src/store/menuStore';

vi.mock('../../src/services/menuService', () => ({
  getMenuVersions: vi.fn(),
  getMenuByVersion: vi.fn(),
  getCurrentMenu: vi.fn(),
  createMenuVersion: vi.fn(),
  formatDateTime: (value) => value,
}));

vi.mock('../../src/store/menuStore', () => ({
  default: vi.fn(),
}));

const renderWithRouter = (component) => {
  return render(<MemoryRouter>{component}</MemoryRouter>);
};

describe('MenuEditor', () => {
  const versions = [{ id: 2, created_at: '2026-02-24T10:00:00Z' }];
  const baseMenu = {
    Salads: [
      { id: 'salads_01', name: 'Greek Salad', price: 9.5, category: 'kitchen' },
    ],
  };

  beforeEach(() => {
    vi.clearAllMocks();
    menuService.getMenuVersions.mockResolvedValue(versions);
    menuService.getMenuByVersion.mockResolvedValue(baseMenu);
    menuService.createMenuVersion.mockResolvedValue({ id: 3 });
    useMenuStore.mockImplementation((selector) => selector({ refreshMenu: vi.fn() }));
  });

  it('renders latest menu version items', async () => {
    renderWithRouter(<MenuEditor />);

    await waitFor(() => {
      expect(screen.getByText('Greek Salad')).toBeInTheDocument();
    });

    expect(screen.getByText('Εκδοση #2')).toBeInTheDocument();
  });

  it('edits an item and refreshes UI with updated data', async () => {
    const updatedMenu = {
      Salads: [
        { id: 'salads_01', name: 'Updated Salad', price: 10.0, category: 'kitchen' },
      ],
    };

    menuService.getMenuByVersion
      .mockResolvedValueOnce(baseMenu)
      .mockResolvedValueOnce(updatedMenu);

    renderWithRouter(<MenuEditor />);

    await waitFor(() => {
      expect(screen.getByText('Greek Salad')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Επεξεργασια'));

    const nameInput = screen.getByLabelText('Ονομα');
    fireEvent.change(nameInput, { target: { value: 'Updated Salad' } });

    fireEvent.click(screen.getByText('Αποθηκευση'));

    await waitFor(() => {
      expect(menuService.createMenuVersion).toHaveBeenCalledWith(
        expect.objectContaining({
          Salads: [
            expect.objectContaining({ name: 'Updated Salad' })
          ]
        })
      );
      expect(screen.getByText('Updated Salad')).toBeInTheDocument();
    });
  });
});

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import Workstations from '../../pages/Admin/Workstations';
import * as workstationsService from '../../services/workstationsService';

// Mock the workstations service
vi.mock('../../services/workstationsService');

describe('Workstations Admin Page', () => {
  const mockWorkstations = [
    {
      id: 1,
      name: 'Grill Station',
      slug: 'grill',
      created_at: '2026-02-24T10:00:00',
      active: true,
    },
    {
      id: 2,
      name: 'Kitchen',
      slug: 'kitchen',
      created_at: '2026-02-24T10:15:00',
      active: true,
    },
    {
      id: 3,
      name: 'Drinks Bar',
      slug: 'drinks',
      created_at: '2026-02-24T10:30:00',
      active: true,
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    workstationsService.listWorkstations.mockResolvedValue(mockWorkstations);
    workstationsService.createWorkstation.mockResolvedValue({
      id: 4,
      name: 'Pastry Station',
      slug: 'pastry',
      created_at: '2026-02-24T11:00:00',
      active: true,
    });
    workstationsService.updateWorkstation.mockResolvedValue({
      id: 1,
      name: 'BBQ Grill',
      slug: 'bbq',
      created_at: '2026-02-24T10:00:00',
      active: true,
    });
    workstationsService.deleteWorkstation.mockResolvedValue({
      status: 'deleted',
      workstation_id: 1,
    });
  });

  it('renders workstations page title and create button', async () => {
    render(<Workstations />);

    await waitFor(() => {
      expect(screen.getByText('Workstations Management')).toBeInTheDocument();
      expect(screen.getByText('+ Create Workstation')).toBeInTheDocument();
    });
  });

  it('loads and displays workstations list', async () => {
    render(<Workstations />);

    await waitFor(() => {
      expect(workstationsService.listWorkstations).toHaveBeenCalled();
      expect(screen.getByText('Grill Station')).toBeInTheDocument();
      expect(screen.getByText('Kitchen')).toBeInTheDocument();
      expect(screen.getByText('Drinks Bar')).toBeInTheDocument();
    });
  });

  it('displays workstation slugs in code format', async () => {
    render(<Workstations />);

    await waitFor(() => {
      const codeElements = screen.getAllByText(/grill|kitchen|drinks/);
      expect(codeElements.length).toBeGreaterThan(0);
    });
  });

  it('displays active status badge', async () => {
    render(<Workstations />);

    await waitFor(() => {
      const activeStatuses = screen.getAllByText('Active');
      expect(activeStatuses.length).toBeGreaterThan(0);
    });
  });

  describe('Create Workstation', () => {
    it('opens create workstation modal when button clicked', async () => {
      render(<Workstations />);

      const createButton = await screen.findByText('+ Create Workstation');
      fireEvent.click(createButton);

      await waitFor(() => {
        expect(screen.getByText('Create Workstation')).toBeInTheDocument();
      });
    });

    it('creates workstation with valid form data', async () => {
      render(<Workstations />);

      const createButton = await screen.findByText('+ Create Workstation');
      fireEvent.click(createButton);

      await waitFor(() => {
        expect(screen.getByText('Create Workstation')).toBeInTheDocument();
      });

      const nameInput = screen.getByPlaceholderText('e.g., Grill Station');
      const slugInput = screen.getByPlaceholderText('e.g., grill (lowercase, no spaces)');
      const submitButton = screen.getByRole('button', { name: 'Create' });

      fireEvent.change(nameInput, { target: { value: 'Pastry Station' } });
      fireEvent.change(slugInput, { target: { value: 'pastry' } });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(workstationsService.createWorkstation).toHaveBeenCalledWith({
          name: 'Pastry Station',
          slug: 'pastry',
        });
        expect(screen.getByText('Workstation "Pastry Station" created successfully')).toBeInTheDocument();
      });
    });

    it('shows validation error for empty name', async () => {
      render(<Workstations />);

      const createButton = await screen.findByText('+ Create Workstation');
      fireEvent.click(createButton);

      await waitFor(() => {
        expect(screen.getByText('Create Workstation')).toBeInTheDocument();
      });

      const submitButton = screen.getByRole('button', { name: 'Create' });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText('Name is required')).toBeInTheDocument();
      });
    });

    it('shows validation error for empty slug', async () => {
      render(<Workstations />);

      const createButton = await screen.findByText('+ Create Workstation');
      fireEvent.click(createButton);

      await waitFor(() => {
        expect(screen.getByText('Create Workstation')).toBeInTheDocument();
      });

      const nameInput = screen.getByPlaceholderText('e.g., Grill Station');
      fireEvent.change(nameInput, { target: { value: 'New Station' } });

      const submitButton = screen.getByRole('button', { name: 'Create' });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText('Slug is required')).toBeInTheDocument();
      });
    });

    it('closes modal when cancel button clicked', async () => {
      render(<Workstations />);

      const createButton = await screen.findByText('+ Create Workstation');
      fireEvent.click(createButton);

      await waitFor(() => {
        expect(screen.getByText('Create Workstation')).toBeInTheDocument();
      });

      const cancelButton = screen.getByRole('button', { name: 'Cancel' });
      fireEvent.click(cancelButton);

      await waitFor(() => {
        expect(screen.queryByText('Create Workstation')).not.toBeInTheDocument();
      });
    });
  });

  describe('Edit Workstation', () => {
    it('enters edit mode when Edit button clicked', async () => {
      render(<Workstations />);

      await waitFor(() => {
        expect(screen.getByText('Grill Station')).toBeInTheDocument();
      });

      const editButtons = screen.getAllByRole('button', { name: 'Edit' });
      fireEvent.click(editButtons[0]);

      await waitFor(() => {
        const inputs = screen.getAllByDisplayValue('Grill Station');
        expect(inputs.length).toBeGreaterThan(0);
      });
    });

    it('saves edited workstation', async () => {
      render(<Workstations />);

      await waitFor(() => {
        expect(screen.getByText('Grill Station')).toBeInTheDocument();
      });

      const editButtons = screen.getAllByRole('button', { name: 'Edit' });
      fireEvent.click(editButtons[0]);

      await waitFor(() => {
        const inputs = screen.getAllByDisplayValue('Grill Station');
        expect(inputs.length).toBeGreaterThan(0);
      });

      const nameInput = screen.getByDisplayValue('Grill Station');
      fireEvent.change(nameInput, { target: { value: 'BBQ Grill' } });

      const saveButtons = screen.getAllByRole('button', { name: 'Save' });
      fireEvent.click(saveButtons[0]);

      await waitFor(() => {
        expect(workstationsService.updateWorkstation).toHaveBeenCalledWith(
          1,
          expect.objectContaining({ name: 'BBQ Grill' })
        );
      });
    });

    it('cancels edit when Cancel button clicked', async () => {
      render(<Workstations />);

      await waitFor(() => {
        expect(screen.getByText('Grill Station')).toBeInTheDocument();
      });

      const editButtons = screen.getAllByRole('button', { name: 'Edit' });
      fireEvent.click(editButtons[0]);

      await waitFor(() => {
        const inputs = screen.getAllByDisplayValue('Grill Station');
        expect(inputs.length).toBeGreaterThan(0);
      });

      const cancelButtons = screen.getAllByRole('button', { name: 'Cancel' });
      fireEvent.click(cancelButtons[0]);

      await waitFor(() => {
        const inputs = screen.queryAllByDisplayValue('Grill Station');
        // After cancel, should go back to display mode which doesn't have input
        expect(screen.getByText('Grill Station')).toBeInTheDocument();
      });
    });
  });

  describe('Toggle Active Status', () => {
    it('deactivates workstation when Deactivate button clicked', async () => {
      render(<Workstations />);

      await waitFor(() => {
        expect(screen.getByText('Grill Station')).toBeInTheDocument();
      });

      // Mock the update to return inactive
      workstationsService.updateWorkstation.mockResolvedValueOnce({
        id: 1,
        name: 'Grill Station',
        slug: 'grill',
        created_at: '2026-02-24T10:00:00',
        active: false,
      });

      const deactivateButtons = screen.getAllByRole('button', { name: 'Deactivate' });
      fireEvent.click(deactivateButtons[0]);

      await waitFor(() => {
        expect(workstationsService.updateWorkstation).toHaveBeenCalledWith(
          1,
          { active: false }
        );
      });
    });
  });

  describe('Delete Workstation', () => {
    it('shows confirmation dialog before deleting', async () => {
      // Mock window.confirm
      const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false);

      render(<Workstations />);

      await waitFor(() => {
        expect(screen.getByText('Grill Station')).toBeInTheDocument();
      });

      const deleteButtons = screen.getAllByRole('button', { name: 'Delete' });
      fireEvent.click(deleteButtons[0]);

      expect(confirmSpy).toHaveBeenCalled();
      expect(workstationsService.deleteWorkstation).not.toHaveBeenCalled();

      confirmSpy.mockRestore();
    });

    it('deletes workstation when confirmed', async () => {
      vi.spyOn(window, 'confirm').mockReturnValue(true);

      render(<Workstations />);

      await waitFor(() => {
        expect(screen.getByText('Grill Station')).toBeInTheDocument();
      });

      const deleteButtons = screen.getAllByRole('button', { name: 'Delete' });
      fireEvent.click(deleteButtons[0]);

      await waitFor(() => {
        expect(workstationsService.deleteWorkstation).toHaveBeenCalledWith(1);
        expect(screen.getByText('Workstation "Grill Station" deleted successfully')).toBeInTheDocument();
      });
    });
  });

  describe('Error Handling', () => {
    it('displays error message when listing fails', async () => {
      workstationsService.listWorkstations.mockRejectedValue(
        new Error('Failed to load workstations')
      );

      render(<Workstations />);

      await waitFor(() => {
        expect(screen.getByText('Failed to load workstations')).toBeInTheDocument();
      });
    });

    it('displays error message when creation fails', async () => {
      workstationsService.createWorkstation.mockRejectedValue(
        new Error('Slug already exists')
      );

      render(<Workstations />);

      const createButton = await screen.findByText('+ Create Workstation');
      fireEvent.click(createButton);

      await waitFor(() => {
        expect(screen.getByText('Create Workstation')).toBeInTheDocument();
      });

      const nameInput = screen.getByPlaceholderText('e.g., Grill Station');
      const slugInput = screen.getByPlaceholderText('e.g., grill (lowercase, no spaces)');
      const submitButton = screen.getByRole('button', { name: 'Create' });

      fireEvent.change(nameInput, { target: { value: 'Grill' } });
      fireEvent.change(slugInput, { target: { value: 'grill' } });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText('Slug already exists')).toBeInTheDocument();
      });
    });
  });

  describe('Empty State', () => {
    it('displays empty state when no workstations', async () => {
      workstationsService.listWorkstations.mockResolvedValue([]);

      render(<Workstations />);

      await waitFor(() => {
        expect(screen.getByText('No workstations found. Create one to get started.')).toBeInTheDocument();
      });
    });
  });
});

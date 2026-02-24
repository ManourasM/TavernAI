import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import Users from './Users';
import * as usersService from '../../services/usersService';

// Mock the users service
vi.mock('../../services/usersService');

describe('Users Admin Page', () => {
  const mockUsers = [
    {
      id: 1,
      username: 'admin_user',
      roles: ['admin'],
      created_at: '2026-02-24T10:00:00',
    },
    {
      id: 2,
      username: 'waiter1',
      roles: ['waiter'],
      created_at: '2026-02-24T10:15:00',
    },
    {
      id: 3,
      username: 'kitchen_user',
      roles: ['station_kitchen'],
      created_at: '2026-02-24T10:30:00',
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    usersService.listUsers.mockResolvedValue(mockUsers);
    usersService.createUser.mockResolvedValue({
      id: 4,
      username: 'new_user',
      roles: ['waiter'],
      created_at: '2026-02-24T11:00:00',
    });
    usersService.updateUser.mockResolvedValue({
      id: 2,
      username: 'waiter1',
      roles: ['waiter', 'station_drinks'],
      created_at: '2026-02-24T10:15:00',
    });
    usersService.deleteUser.mockResolvedValue(undefined);
  });

  it('renders users page title and create button', async () => {
    render(<Users />);

    await waitFor(() => {
      expect(screen.getByText('User Management')).toBeInTheDocument();
      expect(screen.getByText('+ Create User')).toBeInTheDocument();
    });
  });

  it('loads and displays users list', async () => {
    render(<Users />);

    await waitFor(() => {
      expect(usersService.listUsers).toHaveBeenCalled();
      expect(screen.getByText('admin_user')).toBeInTheDocument();
      expect(screen.getByText('waiter1')).toBeInTheDocument();
      expect(screen.getByText('kitchen_user')).toBeInTheDocument();
    });
  });

  it('displays user roles in table', async () => {
    render(<Users />);

    await waitFor(() => {
      expect(screen.getByText('Admin')).toBeInTheDocument();
      expect(screen.getByText('Waiter')).toBeInTheDocument();
      expect(screen.getByText('Kitchen')).toBeInTheDocument();
    });
  });

  describe('Create User', () => {
    it('opens create user modal when button clicked', async () => {
      render(<Users />);

      const createButton = await screen.findByText('+ Create User');
      fireEvent.click(createButton);

      await waitFor(() => {
        expect(screen.getByText('Create New User')).toBeInTheDocument();
      });
    });

    it('creates user when form submitted', async () => {
      render(<Users />);

      const createButton = await screen.findByText('+ Create User');
      fireEvent.click(createButton);

      await waitFor(() => {
        expect(screen.getByText('Create New User')).toBeInTheDocument();
      });

      // Fill in form
      const usernameInput = screen.getByPlaceholderText('Enter username');
      const passwordInput = screen.getByPlaceholderText('Enter password');

      fireEvent.change(usernameInput, { target: { value: 'new_user' } });
      fireEvent.change(passwordInput, { target: { value: 'password123' } });

      // Select waiter role
      const waiterCheckbox = screen.getByRole('checkbox', { name: /waiter/i });
      fireEvent.click(waiterCheckbox);

      // Submit form
      const submitButton = screen.getByRole('button', { name: /Create User/i });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(usersService.createUser).toHaveBeenCalledWith({
          username: 'new_user',
          password: 'password123',
          roles: ['waiter'],
        });
      });
    });

    it('shows success message after creating user', async () => {
      render(<Users />);

      const createButton = await screen.findByText('+ Create User');
      fireEvent.click(createButton);

      await waitFor(() => {
        expect(screen.getByText('Create New User')).toBeInTheDocument();
      });

      // Fill and submit form
      const usernameInput = screen.getByPlaceholderText('Enter username');
      const passwordInput = screen.getByPlaceholderText('Enter password');
      fireEvent.change(usernameInput, { target: { value: 'new_user' } });
      fireEvent.change(passwordInput, { target: { value: 'password123' } });

      const waiterCheckbox = screen.getByRole('checkbox', { name: /waiter/i });
      fireEvent.click(waiterCheckbox);

      const submitButton = screen.getByRole('button', { name: /Create User/i });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/User "new_user" created successfully/)).toBeInTheDocument();
      });
    });

    it('validates required fields', async () => {
      render(<Users />);

      const createButton = await screen.findByText('+ Create User');
      fireEvent.click(createButton);

      await waitFor(() => {
        expect(screen.getByText('Create New User')).toBeInTheDocument();
      });

      // Try to submit without filling fields
      const submitButton = screen.getByRole('button', { name: /Create User/i });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText('Username is required')).toBeInTheDocument();
        expect(screen.getByText('Password is required')).toBeInTheDocument();
        expect(screen.getByText('At least one role must be selected')).toBeInTheDocument();
      });
    });
  });

  describe('Edit User Roles', () => {
    it('opens role edit mode when "Edit Roles" clicked', async () => {
      render(<Users />);

      await waitFor(() => {
        expect(screen.getByText('waiter1')).toBeInTheDocument();
      });

      const editButtons = screen.getAllByText('Edit Roles');
      fireEvent.click(editButtons[0]); // Edit first user (admin)

      await waitFor(() => {
        expect(screen.getAllByRole('checkbox')).toHaveLength(5); // All 5 role checkboxes visible
      });
    });

    it('updates user roles when saved', async () => {
      render(<Users />);

      await waitFor(() => {
        expect(screen.getByText('waiter1')).toBeInTheDocument();
      });

      // Click edit roles for waiter1
      const editButtons = screen.getAllByText('Edit Roles');
      fireEvent.click(editButtons[1]); // waiter1 is second in list

      // Check additional role
      const drinksCheckbox = screen.getByRole('checkbox', { name: /drinks/i });
      fireEvent.click(drinksCheckbox);

      // Save
      const saveButton = screen.getByRole('button', { name: /^Save$/i });
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(usersService.updateUser).toHaveBeenCalledWith(2, {
          roles: ['waiter', 'station_drinks'],
        });
      });
    });

    it('shows success message after updating roles', async () => {
      render(<Users />);

      await waitFor(() => {
        expect(screen.getByText('waiter1')).toBeInTheDocument();
      });

      const editButtons = screen.getAllByText('Edit Roles');
      fireEvent.click(editButtons[1]);

      const drinksCheckbox = screen.getByRole('checkbox', { name: /drinks/i });
      fireEvent.click(drinksCheckbox);

      const saveButton = screen.getByRole('button', { name: /^Save$/i });
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(screen.getByText('User roles updated successfully')).toBeInTheDocument();
      });
    });
  });

  describe('Reset Password', () => {
    it('opens reset password modal when button clicked', async () => {
      render(<Users />);

      await waitFor(() => {
        expect(screen.getByText('waiter1')).toBeInTheDocument();
      });

      const resetButtons = screen.getAllByText('Reset Pwd');
      fireEvent.click(resetButtons[0]);

      await waitFor(() => {
        expect(screen.getByText('Reset Password')).toBeInTheDocument();
      });
    });

    it('resets password when new password submitted', async () => {
      render(<Users />);

      await waitFor(() => {
        expect(screen.getByText('waiter1')).toBeInTheDocument();
      });

      const resetButtons = screen.getAllByText('Reset Pwd');
      fireEvent.click(resetButtons[0]);

      await waitFor(() => {
        expect(screen.getByText('Reset Password')).toBeInTheDocument();
      });

      const passwordInput = screen.getByPlaceholderText('Enter new password');
      fireEvent.change(passwordInput, { target: { value: 'newpassword123' } });

      const saveButton = screen.getByText('Save Password');
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(usersService.updateUser).toHaveBeenCalledWith(1, {
          password: 'newpassword123',
        });
      });
    });

    it('shows success message after resetting password', async () => {
      render(<Users />);

      await waitFor(() => {
        expect(screen.getByText('waiter1')).toBeInTheDocument();
      });

      const resetButtons = screen.getAllByText('Reset Pwd');
      fireEvent.click(resetButtons[0]);

      await waitFor(() => {
        expect(screen.getByText('Reset Password')).toBeInTheDocument();
      });

      const passwordInput = screen.getByPlaceholderText('Enter new password');
      fireEvent.change(passwordInput, { target: { value: 'newpassword123' } });

      const saveButton = screen.getByText('Save Password');
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(screen.getByText(/Password reset for/)).toBeInTheDocument();
      });
    });
  });

  describe('Delete User', () => {
    it('shows confirmation before deleting user', async () => {
      const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false);

      render(<Users />);

      await waitFor(() => {
        expect(screen.getByText('waiter1')).toBeInTheDocument();
      });

      const deleteButtons = screen.getAllByText('Delete');
      fireEvent.click(deleteButtons[0]);

      expect(confirmSpy).toHaveBeenCalled();
      expect(usersService.deleteUser).not.toHaveBeenCalled();

      confirmSpy.mockRestore();
    });

    it('deletes user when confirmed', async () => {
      vi.spyOn(window, 'confirm').mockReturnValue(true);

      render(<Users />);

      await waitFor(() => {
        expect(screen.getByText('waiter1')).toBeInTheDocument();
      });

      const deleteButtons = screen.getAllByText('Delete');
      fireEvent.click(deleteButtons[0]);

      await waitFor(() => {
        expect(usersService.deleteUser).toHaveBeenCalledWith(1);
      });
    });

    it('shows success message after deleting user', async () => {
      vi.spyOn(window, 'confirm').mockReturnValue(true);

      render(<Users />);

      await waitFor(() => {
        expect(screen.getByText('waiter1')).toBeInTheDocument();
      });

      const deleteButtons = screen.getAllByText('Delete');
      fireEvent.click(deleteButtons[0]);

      await waitFor(() => {
        expect(screen.getByText(/deleted successfully/)).toBeInTheDocument();
      });
    });

    it('removes deleted user from list', async () => {
      vi.spyOn(window, 'confirm').mockReturnValue(true);

      render(<Users />);

      await waitFor(() => {
        expect(screen.getByText('admin_user')).toBeInTheDocument();
      });

      const deleteButtons = screen.getAllByText('Delete');
      fireEvent.click(deleteButtons[0]); // Delete admin_user

      await waitFor(() => {
        expect(screen.queryByText('admin_user')).not.toBeInTheDocument();
      });
    });
  });

  it('shows error message when API call fails', async () => {
    usersService.listUsers.mockRejectedValueOnce(
      new Error('API Error: 500 Internal Server Error')
    );

    render(<Users />);

    await waitFor(() => {
      expect(screen.getByText(/API Error/)).toBeInTheDocument();
    });
  });

  it('displays empty state when no users', async () => {
    usersService.listUsers.mockResolvedValueOnce([]);

    render(<Users />);

    await waitFor(() => {
      expect(screen.getByText(/No users found/)).toBeInTheDocument();
    });
  });
});

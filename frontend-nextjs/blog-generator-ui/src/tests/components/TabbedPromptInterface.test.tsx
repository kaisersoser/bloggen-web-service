import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TabbedPromptInterface } from '@/components/blog/TabbedPromptInterface';
import { describe, it, expect, vi } from 'vitest';

describe('TabbedPromptInterface - SSE connection banner', () => {
  const baseProps = {
    onSubmit: vi.fn(),
    remainingGenerations: 3,
    userRole: 'FREE' as const
  };

  const openConsoleTab = async (user: ReturnType<typeof userEvent.setup>) => {
    const consoleTabs = screen.getAllByRole('tab', { name: /console/i });
    await user.click(consoleTabs[consoleTabs.length - 1]);
  };

  it('shows live status banner while generating', async () => {
    render(
      <TabbedPromptInterface
        {...baseProps}
        isGenerating
        connectionStatus={{
          status: 'connecting',
          message: 'Re-establishing connection',
          updatedAt: '2025-01-01T12:00:00.000Z'
        }}
      />
    );

    expect(await screen.findByText('Connecting to live updates…')).toBeInTheDocument();
    expect(screen.getByText(/re-establishing connection/i)).toBeInTheDocument();
  });

  it('hides banner when stream is closed and generation stopped', async () => {
    const user = userEvent.setup();

    render(
      <TabbedPromptInterface
        {...baseProps}
        connectionStatus={{
          status: 'closed',
          message: 'Stream finished',
          updatedAt: '2025-01-01T12:00:00.000Z'
        }}
      />
    );

  await openConsoleTab(user);

    expect(screen.queryByText('Live updates ended')).not.toBeInTheDocument();
  });

  it('shows reconnection warning when not generating but status requires attention', async () => {
    const user = userEvent.setup();

    render(
      <TabbedPromptInterface
        {...baseProps}
        connectionStatus={{
          status: 'reconnecting',
          message: 'Waiting for server heartbeat',
          updatedAt: '2025-01-01T12:00:00.000Z'
        }}
      />
    );

  await openConsoleTab(user);

    expect(screen.getByText('Reconnecting…')).toBeInTheDocument();
    expect(screen.getByText(/waiting for server heartbeat/i)).toBeInTheDocument();
  });
});

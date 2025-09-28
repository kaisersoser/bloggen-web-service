import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { BlogTileGrid } from '@/components/blog/BlogTileGrid';

const baseBlogs = [
  {
    id: '1',
    topic: 'Zeta Adventures',
    instructions: null,
    heroImageUrl: null,
    createdAt: '2024-04-02T12:00:00Z',
    status: 'completed' as const,
    progress: 100,
    content: 'Content A',
  },
  {
    id: '2',
    topic: 'Alpha Beginnings',
    instructions: null,
    heroImageUrl: null,
    createdAt: '2024-05-10T12:00:00Z',
    status: 'completed' as const,
    progress: 100,
    content: 'Content B',
  },
  {
    id: '3',
    topic: 'Midnight Musings',
    instructions: null,
    heroImageUrl: null,
    createdAt: '2024-03-15T12:00:00Z',
    status: 'completed' as const,
    progress: 100,
    content: 'Content C',
  },
];

describe('BlogTileGrid sorting', () => {
  const renderGrid = () => {
    render(
      <BlogTileGrid
        blogs={baseBlogs}
        onBlogView={vi.fn()}
        onBlogDelete={vi.fn()}
        onBulkDeleteBlogs={vi.fn()}
        isLoading={false}
      />
    );
  };

  it('sorts blogs alphabetically A-Z using topic fallback', async () => {
    renderGrid();

  const [sortDropdown] = screen.getAllByRole('combobox');
    await userEvent.selectOptions(sortDropdown, 'title-asc');

    const headings = await screen.findAllByRole('heading', { level: 3 });
    const orderedTopics = headings
      .slice(0, baseBlogs.length)
      .map((heading) => heading.textContent?.trim());

    expect(orderedTopics).toEqual([
      'Alpha Beginnings',
      'Midnight Musings',
      'Zeta Adventures',
    ]);
  });

  it('sorts blogs alphabetically Z-A using topic fallback', async () => {
    renderGrid();

  const [sortDropdown] = screen.getAllByRole('combobox');
    await userEvent.selectOptions(sortDropdown, 'title-desc');

    const headings = await screen.findAllByRole('heading', { level: 3 });
    const orderedTopics = headings
      .slice(0, baseBlogs.length)
      .map((heading) => heading.textContent?.trim());

    expect(orderedTopics).toEqual([
      'Zeta Adventures',
      'Midnight Musings',
      'Alpha Beginnings',
    ]);
  });
});

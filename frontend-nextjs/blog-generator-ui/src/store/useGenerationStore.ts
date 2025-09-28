"use client";

import { create } from 'zustand';
import type { BlogData, LogEntry } from '@/types/blog';

export interface GenerationState {
  currentJobId: string | null;
  generationError: string | null;
  isGenerating: boolean;
  activeConnectionId: string | null;
  taskLogs: Record<string, LogEntry[]>;
  showDeleteDialog: boolean;
  blogToDelete: BlogData | null;
  isDeleting: boolean;
  selectedBlog: BlogData | null;
  showBlogModal: boolean;
  creatingNew: boolean;
}

export interface GenerationStateActions {
  setCurrentJobId: (id: string | null) => void;
  setGenerationError: (message: string | null) => void;
  setIsGenerating: (value: boolean) => void;
  setActiveConnectionId: (id: string | null) => void;
  setTaskLogs: (logs: Record<string, LogEntry[]>) => void;
  appendTaskLog: (taskId: string, log: LogEntry) => void;
  clearTaskLogs: () => void;
  setShowDeleteDialog: (value: boolean) => void;
  setBlogToDelete: (blog: BlogData | null) => void;
  setIsDeleting: (value: boolean) => void;
  setSelectedBlog: (blog: BlogData | null) => void;
  setShowBlogModal: (value: boolean) => void;
  setCreatingNew: (value: boolean) => void;
}

interface GenerationStore extends GenerationState, GenerationStateActions {
  resetState: () => void;
}

const createInitialState = (): GenerationState => ({
  currentJobId: null,
  generationError: null,
  isGenerating: false,
  activeConnectionId: null,
  taskLogs: {},
  showDeleteDialog: false,
  blogToDelete: null,
  isDeleting: false,
  selectedBlog: null,
  showBlogModal: false,
  creatingNew: false,
});

export const useGenerationStore = create<GenerationStore>()((set) => ({
  ...createInitialState(),
  setCurrentJobId: (id) => set({ currentJobId: id }),
  setGenerationError: (message) => set({ generationError: message }),
  setIsGenerating: (value) => set({ isGenerating: value }),
  setActiveConnectionId: (id) => set({ activeConnectionId: id }),
  setTaskLogs: (logs) => set({ taskLogs: logs }),
  appendTaskLog: (taskId, log) =>
    set((state) => {
      const existingLogs = state.taskLogs[taskId] || [];
      return {
        taskLogs: {
          ...state.taskLogs,
          [taskId]: [...existingLogs, log],
        },
      };
    }),
  clearTaskLogs: () => set({ taskLogs: {} }),
  setShowDeleteDialog: (value) => set({ showDeleteDialog: value }),
  setBlogToDelete: (blog) => set({ blogToDelete: blog }),
  setIsDeleting: (value) => set({ isDeleting: value }),
  setSelectedBlog: (blog) => set({ selectedBlog: blog }),
  setShowBlogModal: (value) => set({ showBlogModal: value }),
  setCreatingNew: (value) => set({ creatingNew: value }),
  resetState: () => set(() => createInitialState()),
}));

export const resetGenerationStore = () => {
  const { resetState } = useGenerationStore.getState();
  resetState();
};

export const getGenerationStoreState = () => useGenerationStore.getState();

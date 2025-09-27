import { useMemo, useReducer } from 'react';
import type { BlogData, LogEntry } from '@/types/blog';

interface GenerationState {
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

const defaultState: GenerationState = {
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
};

type Action =
  | { type: 'setCurrentJobId'; payload: string | null }
  | { type: 'setGenerationError'; payload: string | null }
  | { type: 'setIsGenerating'; payload: boolean }
  | { type: 'setActiveConnectionId'; payload: string | null }
  | { type: 'setTaskLogs'; payload: Record<string, LogEntry[]> }
  | { type: 'appendTaskLog'; payload: { taskId: string; log: LogEntry } }
  | { type: 'setShowDeleteDialog'; payload: boolean }
  | { type: 'setBlogToDelete'; payload: BlogData | null }
  | { type: 'setIsDeleting'; payload: boolean }
  | { type: 'setSelectedBlog'; payload: BlogData | null }
  | { type: 'setShowBlogModal'; payload: boolean }
  | { type: 'setCreatingNew'; payload: boolean }
  | { type: 'resetTaskLogs' };

function reducer(state: GenerationState, action: Action): GenerationState {
  switch (action.type) {
    case 'setCurrentJobId':
      return { ...state, currentJobId: action.payload };
    case 'setGenerationError':
      return { ...state, generationError: action.payload };
    case 'setIsGenerating':
      return { ...state, isGenerating: action.payload };
    case 'setActiveConnectionId':
      return { ...state, activeConnectionId: action.payload };
    case 'setTaskLogs':
      return { ...state, taskLogs: action.payload };
    case 'appendTaskLog': {
      const { taskId, log } = action.payload;
      const existingLogs = state.taskLogs[taskId] || [];
      return {
        ...state,
        taskLogs: {
          ...state.taskLogs,
          [taskId]: [...existingLogs, log],
        },
      };
    }
    case 'setShowDeleteDialog':
      return { ...state, showDeleteDialog: action.payload };
    case 'setBlogToDelete':
      return { ...state, blogToDelete: action.payload };
    case 'setIsDeleting':
      return { ...state, isDeleting: action.payload };
    case 'setSelectedBlog':
      return { ...state, selectedBlog: action.payload };
    case 'setShowBlogModal':
      return { ...state, showBlogModal: action.payload };
    case 'setCreatingNew':
      return { ...state, creatingNew: action.payload };
    case 'resetTaskLogs':
      return { ...state, taskLogs: {} };
    default:
      return state;
  }
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

export function useGenerationStateManager(initialState?: Partial<GenerationState>) {
  const [state, dispatch] = useReducer(reducer, {
    ...defaultState,
    ...initialState,
  });

  const actions: GenerationStateActions = useMemo(() => ({
    setCurrentJobId: (id) => dispatch({ type: 'setCurrentJobId', payload: id }),
    setGenerationError: (message) => dispatch({ type: 'setGenerationError', payload: message }),
    setIsGenerating: (value) => dispatch({ type: 'setIsGenerating', payload: value }),
    setActiveConnectionId: (id) => dispatch({ type: 'setActiveConnectionId', payload: id }),
    setTaskLogs: (logs) => dispatch({ type: 'setTaskLogs', payload: logs }),
    appendTaskLog: (taskId, log) => dispatch({ type: 'appendTaskLog', payload: { taskId, log } }),
    clearTaskLogs: () => dispatch({ type: 'resetTaskLogs' }),
    setShowDeleteDialog: (value) => dispatch({ type: 'setShowDeleteDialog', payload: value }),
    setBlogToDelete: (blog) => dispatch({ type: 'setBlogToDelete', payload: blog }),
    setIsDeleting: (value) => dispatch({ type: 'setIsDeleting', payload: value }),
    setSelectedBlog: (blog) => dispatch({ type: 'setSelectedBlog', payload: blog }),
    setShowBlogModal: (value) => dispatch({ type: 'setShowBlogModal', payload: value }),
    setCreatingNew: (value) => dispatch({ type: 'setCreatingNew', payload: value }),
  }), []);

  return { state, actions } as const;
}

export type { GenerationState };

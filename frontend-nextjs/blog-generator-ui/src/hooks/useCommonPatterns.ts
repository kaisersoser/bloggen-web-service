/**
 * Custom React Hooks for Common State Management Patterns
 * 
 * Reduces boilerplate code by providing reusable hooks for frequently used
 * state patterns like loading states, error handling, and API data fetching.
 */

import { useState, useEffect, useCallback, useRef } from 'react';

// Define types locally to avoid import issues
interface ApiResponse<T = any> {
  data?: T;
  error?: string;
  message?: string;
  success: boolean;
}

class ApiError extends Error {
  public status: number;
  public code?: string;
  public details?: any;

  constructor(message: string, status: number, code?: string, details?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

// Generic loading, error, and data state pattern
export interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

// Hook for managing async operations (API calls, etc.)
export function useAsyncState<T>(initialData: T | null = null): [
  AsyncState<T>,
  {
    setData: (data: T | null) => void;
    setLoading: (loading: boolean) => void;
    setError: (error: string | null) => void;
    reset: () => void;
    execute: (asyncFn: () => Promise<T>) => Promise<T | null>;
  }
] {
  const [data, setData] = useState<T | null>(initialData);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reset = useCallback(() => {
    setData(initialData);
    setLoading(false);
    setError(null);
  }, [initialData]);

  const execute = useCallback(async (asyncFn: () => Promise<T>): Promise<T | null> => {
    setLoading(true);
    setError(null);
    
    try {
      const result = await asyncFn();
      setData(result);
      setLoading(false);
      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An error occurred';
      setError(errorMessage);
      setLoading(false);
      return null;
    }
  }, []);

  return [
    { data, loading, error },
    { setData, setLoading, setError, reset, execute }
  ];
}

// Hook for API calls with automatic loading/error handling
export function useApiCall<T>(
  apiCall: () => Promise<ApiResponse<T>>,
  dependencies: any[] = [],
  immediate: boolean = true
): [
  AsyncState<T>,
  {
    refetch: () => Promise<void>;
    reset: () => void;
  }
] {
  const [state, actions] = useAsyncState<T>();
  const mountedRef = useRef(true);

  const fetchData = useCallback(async () => {
    if (!mountedRef.current) return;

    actions.setLoading(true);
    actions.setError(null);

    try {
      const response = await apiCall();
      if (!mountedRef.current) return;

      if (response.success && response.data) {
        actions.setData(response.data);
      } else {
        actions.setError('Failed to fetch data');
      }
    } catch (err) {
      if (!mountedRef.current) return;
      
      const errorMessage = err instanceof ApiError 
        ? err.message 
        : err instanceof Error 
        ? err.message 
        : 'An unexpected error occurred';
      actions.setError(errorMessage);
    } finally {
      if (mountedRef.current) {
        actions.setLoading(false);
      }
    }
  }, [apiCall, actions]);

  // Auto-fetch on mount and dependency changes
  useEffect(() => {
    if (immediate) {
      fetchData();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, dependencies);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const refetch = useCallback(async () => {
    await fetchData();
  }, [fetchData]);

  return [state, { refetch, reset: actions.reset }];
}

// Hook for form state management with validation
export interface FormField<T> {
  value: T;
  error: string | null;
  touched: boolean;
}

export interface FormState<T extends Record<string, any>> {
  fields: { [K in keyof T]: FormField<T[K]> };
  isValid: boolean;
  isSubmitting: boolean;
  submitError: string | null;
}

export function useForm<T extends Record<string, any>>(
  initialValues: T,
  validationRules?: { [K in keyof T]?: (value: T[K]) => string | null }
): [
  FormState<T>,
  {
    setValue: <K extends keyof T>(field: K, value: T[K]) => void;
    setTouched: <K extends keyof T>(field: K, touched?: boolean) => void;
    setSubmitting: (submitting: boolean) => void;
    setSubmitError: (error: string | null) => void;
    handleSubmit: (onSubmit: (values: T) => Promise<void> | void) => (e?: React.FormEvent) => Promise<void>;
    reset: () => void;
    getFieldProps: <K extends keyof T>(field: K) => {
      value: T[K];
      onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => void;
      onBlur: () => void;
      error: string | null;
    };
  }
] {
  const [fields, setFields] = useState<{ [K in keyof T]: FormField<T[K]> }>(() => {
    const initialFields: any = {};
    for (const key in initialValues) {
      initialFields[key] = {
        value: initialValues[key],
        error: null,
        touched: false,
      };
    }
    return initialFields;
  });

  const [isSubmitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const validateField = useCallback(<K extends keyof T>(field: K, value: T[K]): string | null => {
    if (validationRules && validationRules[field]) {
      return validationRules[field]!(value);
    }
    return null;
  }, [validationRules]);

  const setValue = useCallback(<K extends keyof T>(field: K, value: T[K]) => {
    setFields(prev => ({
      ...prev,
      [field]: {
        ...prev[field],
        value,
        error: validateField(field, value),
      },
    }));
  }, [validateField]);

  const setTouched = useCallback(<K extends keyof T>(field: K, touched: boolean = true) => {
    setFields(prev => ({
      ...prev,
      [field]: {
        ...prev[field],
        touched,
      },
    }));
  }, []);

  const reset = useCallback(() => {
    const resetFields: any = {};
    for (const key in initialValues) {
      resetFields[key] = {
        value: initialValues[key],
        error: null,
        touched: false,
      };
    }
    setFields(resetFields);
    setSubmitting(false);
    setSubmitError(null);
  }, [initialValues]);

  const isValid = Object.values(fields).every(field => !field.error);

  const handleSubmit = useCallback((onSubmit: (values: T) => Promise<void> | void) => {
    return async (e?: React.FormEvent) => {
      if (e) {
        e.preventDefault();
      }

      // Mark all fields as touched
      const touchedFields: any = {};
      for (const key in fields) {
        touchedFields[key] = {
          ...fields[key],
          touched: true,
        };
      }
      setFields(touchedFields);

      if (!isValid) return;

      setSubmitting(true);
      setSubmitError(null);

      try {
        const values: any = {};
        for (const key in fields) {
          values[key] = fields[key].value;
        }
        await onSubmit(values);
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Submission failed';
        setSubmitError(errorMessage);
      } finally {
        setSubmitting(false);
      }
    };
  }, [fields, isValid]);

  const getFieldProps = useCallback(<K extends keyof T>(field: K) => ({
    value: fields[field].value,
    onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
      setValue(field, e.target.value as T[K]);
    },
    onBlur: () => setTouched(field),
    error: fields[field].touched ? fields[field].error : null,
  }), [fields, setValue, setTouched]);

  return [
    {
      fields,
      isValid,
      isSubmitting,
      submitError,
    },
    {
      setValue,
      setTouched,
      setSubmitting,
      setSubmitError: setSubmitError,
      handleSubmit,
      reset,
      getFieldProps,
    }
  ];
}

// Hook for debounced values (useful for search inputs)
export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

// Hook for local storage with type safety
export function useLocalStorage<T>(
  key: string,
  initialValue: T
): [T, (value: T | ((val: T) => T)) => void] {
  const [storedValue, setStoredValue] = useState<T>(() => {
    try {
      const item = window.localStorage.getItem(key);
      return item ? JSON.parse(item) : initialValue;
    } catch (error) {
      console.warn(`Error reading localStorage key "${key}":`, error);
      return initialValue;
    }
  });

  const setValue = useCallback((value: T | ((val: T) => T)) => {
    try {
      const valueToStore = value instanceof Function ? value(storedValue) : value;
      setStoredValue(valueToStore);
      window.localStorage.setItem(key, JSON.stringify(valueToStore));
    } catch (error) {
      console.warn(`Error setting localStorage key "${key}":`, error);
    }
  }, [key, storedValue]);

  return [storedValue, setValue];
}

// Hook for toggle state (boolean with toggle function)
export function useToggle(initialValue: boolean = false): [boolean, () => void, (value: boolean) => void] {
  const [value, setValue] = useState(initialValue);
  
  const toggle = useCallback(() => setValue(v => !v), []);
  
  return [value, toggle, setValue];
}

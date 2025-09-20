"use client"

import { SSEConnectionTester } from '@/components/diagnostics/SSEConnectionTester';

export default function SSETestPage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">
            SSE Connection Diagnostics
          </h1>
          <p className="text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
            Test and monitor Server-Sent Events connections to the backend notification system.
            Use this tool to diagnose real-time communication issues and monitor message flow.
          </p>
        </div>
        
        <div className="flex justify-center">
          <SSEConnectionTester />
        </div>
        
        <div className="mt-8 text-center text-sm text-gray-500 dark:text-gray-400">
          <p>
            <strong>Day 1 Implementation:</strong> Frontend SSE Connection Diagnostics
          </p>
          <p>
            This component tests authentication, connection establishment, and message reception.
          </p>
        </div>
      </div>
    </div>
  );
}
import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { BlogData } from '@/types/blog';

interface ConfirmDeleteModalProps {
  isOpen: boolean;
  selectedBlogs: BlogData[];
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDeleteModal({ 
  isOpen, 
  selectedBlogs, 
  onConfirm, 
  onCancel 
}: ConfirmDeleteModalProps) {
  const [confirmText, setConfirmText] = useState('');
  const isValidConfirmation = confirmText === 'DELETE';
  
  const handleConfirm = () => {
    if (isValidConfirmation) {
      onConfirm();
      setConfirmText(''); // Reset for next time
    }
  };

  const handleCancel = () => {
    setConfirmText(''); // Reset for next time
    onCancel();
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleCancel}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="text-red-600 dark:text-red-400">
            Delete {selectedBlogs.length} Blog{selectedBlogs.length > 1 ? 's' : ''}?
          </DialogTitle>
          <DialogDescription>
            This action cannot be undone. The following blogs will be permanently deleted:
          </DialogDescription>
        </DialogHeader>
        
        {/* Preview of blogs to delete */}
        <div className="max-h-32 overflow-y-auto space-y-1 border rounded-md p-2 bg-gray-50 dark:bg-gray-800">
          {selectedBlogs.map(blog => (
            <div 
              key={blog.id} 
              className="text-sm p-2 bg-white dark:bg-gray-700 rounded border border-gray-200 dark:border-gray-600"
            >
              <div className="font-medium truncate">{blog.topic}</div>
              <div className="text-xs text-gray-500 dark:text-gray-400">
                {new Date(blog.createdAt).toLocaleDateString()}
              </div>
            </div>
          ))}
        </div>
        
        {/* Confirmation input */}
        <div className="space-y-2">
          <div className="text-sm font-medium">
            Type <span className="font-bold text-red-600 dark:text-red-400">DELETE</span> to confirm:
          </div>
          <Input
            id="confirm-delete"
            value={confirmText}
            onChange={(e) => setConfirmText(e.target.value)}
            placeholder="DELETE"
            className="font-mono"
            autoComplete="off"
          />
        </div>
        
        <DialogFooter>
          <Button variant="outline" onClick={handleCancel}>
            Cancel
          </Button>
          <Button 
            variant="destructive" 
            disabled={!isValidConfirmation}
            onClick={handleConfirm}
          >
            Delete {selectedBlogs.length} Blog{selectedBlogs.length > 1 ? 's' : ''}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

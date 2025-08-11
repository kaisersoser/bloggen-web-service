"use client"

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"

interface DeleteConfirmationDialogProps {
  isOpen: boolean
  onClose: () => void
  onConfirm: () => void
  blogTopic: string
  isDeleting: boolean
}

export function DeleteConfirmationDialog({
  isOpen,
  onClose,
  onConfirm,
  blogTopic,
  isDeleting
}: DeleteConfirmationDialogProps) {
  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Delete Blog Forever?</DialogTitle>
          <DialogDescription>
            Are you sure you want to permanently delete this blog?
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-3 pt-2">
          <div className="font-semibold text-gray-900 bg-gray-100 p-3 rounded border-l-4 border-red-500">
            &quot;{blogTopic}&quot;
          </div>
          <p className="text-red-600 font-medium text-sm">
            ⚠️ This action cannot be undone. The generated blog content will be lost forever.
          </p>
        </div>
        <DialogFooter className="gap-2">
          <Button
            variant="outline"
            onClick={onClose}
            disabled={isDeleting}
          >
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={onConfirm}
            disabled={isDeleting}
          >
            {isDeleting ? (
              <div className="flex items-center space-x-2">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                <span>Deleting...</span>
              </div>
            ) : (
              "Delete Forever"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

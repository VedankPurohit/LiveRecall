import { useState, useCallback } from 'react';

export interface UseSelectionReturn<T extends { id: number }> {
  selectedIds: Set<number>;
  selectedCount: number;
  isSelected: (id: number) => boolean;
  toggleSelection: (id: number, index: number, shiftKey: boolean) => void;
  clearSelection: () => void;
  selectAll: () => void;
  getSelectedIds: () => number[];
}

export function useSelection<T extends { id: number }>(items: T[]): UseSelectionReturn<T> {
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  // Store last selected ID instead of index to handle prepending/deleting items correctly
  const [lastSelectedId, setLastSelectedId] = useState<number | null>(null);

  const isSelected = useCallback(
    (id: number) => selectedIds.has(id),
    [selectedIds]
  );

  const toggleSelection = useCallback(
    (id: number, index: number, shiftKey: boolean) => {
      setSelectedIds((prev) => {
        const next = new Set(prev);

        if (shiftKey && lastSelectedId !== null) {
          // Range selection - find index of last selected item in current items array
          const lastIndex = items.findIndex(item => item.id === lastSelectedId);
          const currentIndex = index;

          if (lastIndex !== -1) {
            // Both items exist in the list, select the range
            const start = Math.min(lastIndex, currentIndex);
            const end = Math.max(lastIndex, currentIndex);
            for (let i = start; i <= end; i++) {
              if (items[i]) {
                next.add(items[i].id);
              }
            }
          } else {
            // Last selected item no longer in list, just select current
            next.add(id);
          }
        } else {
          // Toggle single
          if (next.has(id)) {
            next.delete(id);
          } else {
            next.add(id);
          }
        }

        return next;
      });
      setLastSelectedId(id);
    },
    [items, lastSelectedId]
  );

  const clearSelection = useCallback(() => {
    setSelectedIds(new Set());
    setLastSelectedId(null);
  }, []);

  const selectAll = useCallback(() => {
    setSelectedIds(new Set(items.map((item) => item.id)));
  }, [items]);

  const getSelectedIds = useCallback(() => Array.from(selectedIds), [selectedIds]);

  return {
    selectedIds,
    selectedCount: selectedIds.size,
    isSelected,
    toggleSelection,
    clearSelection,
    selectAll,
    getSelectedIds,
  };
}

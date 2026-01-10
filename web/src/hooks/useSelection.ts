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
  const [lastSelectedIndex, setLastSelectedIndex] = useState<number | null>(null);

  const isSelected = useCallback(
    (id: number) => selectedIds.has(id),
    [selectedIds]
  );

  const toggleSelection = useCallback(
    (id: number, index: number, shiftKey: boolean) => {
      setSelectedIds((prev) => {
        const next = new Set(prev);

        if (shiftKey && lastSelectedIndex !== null) {
          // Range selection
          const start = Math.min(lastSelectedIndex, index);
          const end = Math.max(lastSelectedIndex, index);
          for (let i = start; i <= end; i++) {
            if (items[i]) {
              next.add(items[i].id);
            }
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
      setLastSelectedIndex(index);
    },
    [items, lastSelectedIndex]
  );

  const clearSelection = useCallback(() => {
    setSelectedIds(new Set());
    setLastSelectedIndex(null);
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

/**
 * Tests for hooks/useSelection.ts
 */

import { renderHook, act } from '@testing-library/react';
import { useSelection } from '@/hooks/useSelection';

interface TestItem {
  id: number;
  name: string;
}

const createItems = (count: number, startId: number = 1): TestItem[] => {
  return Array.from({ length: count }, (_, i) => ({
    id: startId + i,
    name: `Item ${startId + i}`,
  }));
};

describe('useSelection', () => {
  describe('basic selection', () => {
    it('should initialize with empty selection', () => {
      const items = createItems(5);
      const { result } = renderHook(() => useSelection(items));

      expect(result.current.selectedCount).toBe(0);
      expect(result.current.selectedIds.size).toBe(0);
    });

    it('should toggle selection of single item', () => {
      const items = createItems(5);
      const { result } = renderHook(() => useSelection(items));

      act(() => {
        result.current.toggleSelection(1, 0, false);
      });

      expect(result.current.selectedCount).toBe(1);
      expect(result.current.isSelected(1)).toBe(true);
      expect(result.current.isSelected(2)).toBe(false);
    });

    it('should deselect when toggling already selected item', () => {
      const items = createItems(5);
      const { result } = renderHook(() => useSelection(items));

      act(() => {
        result.current.toggleSelection(1, 0, false);
      });
      expect(result.current.isSelected(1)).toBe(true);

      act(() => {
        result.current.toggleSelection(1, 0, false);
      });
      expect(result.current.isSelected(1)).toBe(false);
      expect(result.current.selectedCount).toBe(0);
    });

    it('should select multiple items individually', () => {
      const items = createItems(5);
      const { result } = renderHook(() => useSelection(items));

      act(() => {
        result.current.toggleSelection(1, 0, false);
        result.current.toggleSelection(3, 2, false);
        result.current.toggleSelection(5, 4, false);
      });

      expect(result.current.selectedCount).toBe(3);
      expect(result.current.isSelected(1)).toBe(true);
      expect(result.current.isSelected(2)).toBe(false);
      expect(result.current.isSelected(3)).toBe(true);
      expect(result.current.isSelected(4)).toBe(false);
      expect(result.current.isSelected(5)).toBe(true);
    });
  });

  describe('range selection with shift key', () => {
    it('should select range when shift-clicking', () => {
      const items = createItems(5);
      const { result } = renderHook(() => useSelection(items));

      // Select first item
      act(() => {
        result.current.toggleSelection(1, 0, false);
      });

      // Shift-click on item 4
      act(() => {
        result.current.toggleSelection(4, 3, true);
      });

      // Should select items 1, 2, 3, 4
      expect(result.current.selectedCount).toBe(4);
      expect(result.current.isSelected(1)).toBe(true);
      expect(result.current.isSelected(2)).toBe(true);
      expect(result.current.isSelected(3)).toBe(true);
      expect(result.current.isSelected(4)).toBe(true);
      expect(result.current.isSelected(5)).toBe(false);
    });

    it('should select range in reverse order', () => {
      const items = createItems(5);
      const { result } = renderHook(() => useSelection(items));

      // Select item 4 first
      act(() => {
        result.current.toggleSelection(4, 3, false);
      });

      // Shift-click on item 1
      act(() => {
        result.current.toggleSelection(1, 0, true);
      });

      // Should select items 1, 2, 3, 4
      expect(result.current.selectedCount).toBe(4);
      expect(result.current.isSelected(1)).toBe(true);
      expect(result.current.isSelected(2)).toBe(true);
      expect(result.current.isSelected(3)).toBe(true);
      expect(result.current.isSelected(4)).toBe(true);
    });
  });

  describe('range selection with ID-based tracking (prepend/delete resilience)', () => {
    it('should correctly select range after items are prepended', () => {
      // Start with items 1-5
      const initialItems = createItems(5, 1);
      const { result, rerender } = renderHook(
        ({ items }) => useSelection(items),
        { initialProps: { items: initialItems } }
      );

      // Select item with id=3 (index 2)
      act(() => {
        result.current.toggleSelection(3, 2, false);
      });

      // Prepend 2 new items (ids 101, 102)
      // Now the array is: [101, 102, 1, 2, 3, 4, 5]
      const prependedItems = [
        { id: 101, name: 'Prepended 1' },
        { id: 102, name: 'Prepended 2' },
        ...initialItems,
      ];
      rerender({ items: prependedItems });

      // Shift-click on item with id=5 (now at index 6)
      // The range should be from id=3 (now index 4) to id=5 (index 6)
      act(() => {
        result.current.toggleSelection(5, 6, true);
      });

      // Should select items 3, 4, 5 (indices 4, 5, 6 in new array)
      expect(result.current.isSelected(3)).toBe(true);
      expect(result.current.isSelected(4)).toBe(true);
      expect(result.current.isSelected(5)).toBe(true);
      // Should NOT select prepended items
      expect(result.current.isSelected(101)).toBe(false);
      expect(result.current.isSelected(102)).toBe(false);
    });

    it('should correctly select range after items are deleted', () => {
      // Start with items 1-5
      const initialItems = createItems(5, 1);
      const { result, rerender } = renderHook(
        ({ items }) => useSelection(items),
        { initialProps: { items: initialItems } }
      );

      // Select item with id=2 (index 1)
      act(() => {
        result.current.toggleSelection(2, 1, false);
      });

      // Delete item 3 from the middle
      // Now the array is: [1, 2, 4, 5]
      const filteredItems = initialItems.filter(item => item.id !== 3);
      rerender({ items: filteredItems });

      // Shift-click on item with id=5 (now at index 3)
      act(() => {
        result.current.toggleSelection(5, 3, true);
      });

      // Should select items 2, 4, 5 (all items between id=2 and id=5 in current array)
      expect(result.current.isSelected(2)).toBe(true);
      expect(result.current.isSelected(4)).toBe(true);
      expect(result.current.isSelected(5)).toBe(true);
      expect(result.current.isSelected(1)).toBe(false);
    });

    it('should select only current item when last selected item is no longer in list', () => {
      const initialItems = createItems(5, 1);
      const { result, rerender } = renderHook(
        ({ items }) => useSelection(items),
        { initialProps: { items: initialItems } }
      );

      // Select item with id=3
      act(() => {
        result.current.toggleSelection(3, 2, false);
      });

      // Remove item 3 from the list entirely
      const filteredItems = initialItems.filter(item => item.id !== 3);
      rerender({ items: filteredItems });

      // Shift-click on item 5 - since item 3 is gone, should just select item 5
      act(() => {
        result.current.toggleSelection(5, 3, true);
      });

      // Should only have item 5 selected (plus original item 3 which is still in selectedIds)
      expect(result.current.isSelected(5)).toBe(true);
      // Item 3 is still technically "selected" in the Set, but it's not in the list
      expect(result.current.selectedIds.has(3)).toBe(true);
    });
  });

  describe('clearSelection', () => {
    it('should clear all selections', () => {
      const items = createItems(5);
      const { result } = renderHook(() => useSelection(items));

      act(() => {
        result.current.toggleSelection(1, 0, false);
        result.current.toggleSelection(3, 2, false);
      });
      expect(result.current.selectedCount).toBe(2);

      act(() => {
        result.current.clearSelection();
      });

      expect(result.current.selectedCount).toBe(0);
      expect(result.current.isSelected(1)).toBe(false);
      expect(result.current.isSelected(3)).toBe(false);
    });

    it('should reset last selected ID when clearing', () => {
      const items = createItems(5);
      const { result } = renderHook(() => useSelection(items));

      // Select item 1
      act(() => {
        result.current.toggleSelection(1, 0, false);
      });

      // Clear selection
      act(() => {
        result.current.clearSelection();
      });

      // Shift-click on item 3 should only select item 3 (no range from previous)
      act(() => {
        result.current.toggleSelection(3, 2, true);
      });

      expect(result.current.selectedCount).toBe(1);
      expect(result.current.isSelected(3)).toBe(true);
    });
  });

  describe('selectAll', () => {
    it('should select all items', () => {
      const items = createItems(5);
      const { result } = renderHook(() => useSelection(items));

      act(() => {
        result.current.selectAll();
      });

      expect(result.current.selectedCount).toBe(5);
      items.forEach(item => {
        expect(result.current.isSelected(item.id)).toBe(true);
      });
    });

    it('should update selection when items change after selectAll', () => {
      const initialItems = createItems(3);
      const { result, rerender } = renderHook(
        ({ items }) => useSelection(items),
        { initialProps: { items: initialItems } }
      );

      act(() => {
        result.current.selectAll();
      });
      expect(result.current.selectedCount).toBe(3);

      // Add more items
      const newItems = createItems(5);
      rerender({ items: newItems });

      // Selection count is still 3 (IDs 1, 2, 3 are still selected)
      expect(result.current.selectedCount).toBe(3);

      // Select all again to include new items
      act(() => {
        result.current.selectAll();
      });
      expect(result.current.selectedCount).toBe(5);
    });
  });

  describe('getSelectedIds', () => {
    it('should return array of selected IDs', () => {
      const items = createItems(5);
      const { result } = renderHook(() => useSelection(items));

      act(() => {
        result.current.toggleSelection(2, 1, false);
        result.current.toggleSelection(4, 3, false);
      });

      const selectedIds = result.current.getSelectedIds();
      expect(selectedIds).toHaveLength(2);
      expect(selectedIds).toContain(2);
      expect(selectedIds).toContain(4);
    });

    it('should return empty array when nothing selected', () => {
      const items = createItems(5);
      const { result } = renderHook(() => useSelection(items));

      expect(result.current.getSelectedIds()).toEqual([]);
    });
  });
});

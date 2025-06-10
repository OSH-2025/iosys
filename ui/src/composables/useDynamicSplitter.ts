import { ref, onMounted, onUnmounted } from 'vue';
import { useLocalStorage } from '@vueuse/core';

export interface SplitterOptions {
  storageKey: string;
  defaultWidth: number;
  minWidth?: number;
  maxWidth?: number;
}

export function useDynamicSplitter(options: SplitterOptions) {
  const {
    storageKey,
    defaultWidth,
    minWidth = 200,
    maxWidth = 600
  } = options;

  const width = useLocalStorage(storageKey, defaultWidth);
  const isResizing = ref(false);

  const startResize = (e: MouseEvent) => {
    isResizing.value = true;
    document.addEventListener('mousemove', handleResize);
    document.addEventListener('mouseup', stopResize);
    document.body.style.userSelect = 'none';
    e.preventDefault();
  };

  const handleResize = (e: MouseEvent) => {
    if (!isResizing.value) return;
    
    const newWidth = Math.max(minWidth, Math.min(maxWidth, e.clientX));
    width.value = newWidth;
  };

  const stopResize = () => {
    isResizing.value = false;
    document.removeEventListener('mousemove', handleResize);
    document.removeEventListener('mouseup', stopResize);
    document.body.style.userSelect = '';
  };

  onMounted(() => {
    // Ensure width is within bounds on mount
    width.value = Math.max(minWidth, Math.min(maxWidth, width.value));
  });

  onUnmounted(() => {
    document.removeEventListener('mousemove', handleResize);
    document.removeEventListener('mouseup', stopResize);
  });

  return {
    width,
    isResizing,
    startResize
  };
}

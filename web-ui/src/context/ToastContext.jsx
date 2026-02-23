import { createContext, useContext, useState, useCallback } from 'react';
import { X, AlertCircle, CheckCircle, Info } from 'lucide-react';

const ToastContext = createContext(null);

export const useToast = () => {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
};

export const ToastProvider = ({ children }) => {
  const [toasts, setToasts] = useState([]);

  const addToast = useCallback((message, type = 'error', duration = 5000) => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, duration);
  }, []);

  const removeToast = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  const success = useCallback((message) => addToast(message, 'success'), [addToast]);
  const error = useCallback((message) => addToast(message, 'error'), [addToast]);
  const info = useCallback((message) => addToast(message, 'info'), [addToast]);

  return (
    <ToastContext.Provider value={{ addToast, success, error, info, removeToast }}>
      {children}
      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </ToastContext.Provider>
  );
};

const ToastContainer = ({ toasts, onRemove }) => {
  if (toasts.length === 0) return null;

  const icons = {
    error: <AlertCircle className="w-5 h-5 text-rose-400" />,
    success: <CheckCircle className="w-5 h-5 text-emerald-400" />,
    info: <Info className="w-5 h-5 text-tennis-blue" />
  };

  const styles = {
    error: 'bg-rose-500/10 border-rose-500/30',
    success: 'bg-emerald-500/10 border-emerald-500/30',
    info: 'bg-tennis-blue/10 border-tennis-blue/30'
  };

  return (
    <div className="fixed top-4 right-4 z-[100] flex flex-col gap-2 max-w-sm">
      {toasts.map(toast => (
        <div
          key={toast.id}
          className={`flex items-start gap-3 p-4 rounded-lg border shadow-lg animate-in slide-in-from-right ${styles[toast.type]}`}
        >
          {icons[toast.type]}
          <p className="flex-1 text-sm text-white">{toast.message}</p>
          <button
            onClick={() => onRemove(toast.id)}
            className="text-slate-400 hover:text-white transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      ))}
    </div>
  );
};

export default ToastProvider;

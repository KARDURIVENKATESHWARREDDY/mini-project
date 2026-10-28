/**
 * Typed API client for CARD-Net backend.
 * All requests go through Next.js /api/* proxy which forwards to FastAPI.
 */
import axios, { AxiosInstance, AxiosError } from "axios";
import { useAuthStore } from "@/store/auth";

// ── Types ────────────────────────────────────────────────────────────────────

export interface UserInfo {
  id: string;
  email: string;
  full_name: string;
  role: "admin" | "analyst" | "viewer";
  last_login_at?: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: UserInfo;
}

export interface DashboardSummary {
  total_transactions: number;
  high_risk_count: number;
  confirmed_fraud_count: number;
  pending_review_count: number;
  open_investigations: number;
  active_model?: {
    id: string;
    name: string;
    version_tag: string;
    channel: string;
  };
  latest_metrics?: {
    precision?: number;
    recall?: number;
    f1_score?: number;
    pr_auc?: number;
    roc_auc?: number;
  };
}

export interface TimeSeriesPoint { date: string; value: number; }
export interface RiskDistribution { low: number; medium: number; high: number; }
export interface RecentAlert {
  prediction_id: string;
  transaction_id: string;
  fraud_probability: number;
  risk_category: string;
  amount?: number;
  predicted_at: string;
  review_status: string;
}
export interface ModelHealthStatus {
  tab_net_available: boolean;
  seq_net_available: boolean;
  geo_net_available: boolean;
  prof_net_available: boolean;
  fusion_available: boolean;
  active_model_name?: string;
  active_model_version?: string;
  notes?: string;
}

export interface TransactionListItem {
  id: string;
  external_id?: string;
  amount?: number;
  time_seconds?: number;
  imported_at: string;
  fraud_probability?: number;
  risk_category?: string;
  review_status?: string;
  model_version?: string;
  ground_truth_label?: number;
}

export interface PaginatedResponse<T> {
  total: number;
  page: number;
  page_size: number;
  items: T[];
}

export interface PredictionResult {
  prediction_id?: string;
  transaction_id?: string;
  fraud_probability: number;
  risk_category: string;
  model_name: string;
  model_version: string;
  channel: string;
  threshold_low: number;
  threshold_high: number;
  thresholds_validated: boolean;
  shap_values?: Record<string, number>;
  predicted_at: string;
  warnings: string[];
}

export interface BatchJobStatus {
  id: string;
  filename: string;
  status: string;
  total_rows?: number;
  processed_rows: number;
  rejected_rows: number;
  skipped_rows: number;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  error_message?: string;
}

export interface ModelVersion {
  id: string;
  name: string;
  channel: string;
  version_tag: string;
  description?: string;
  artifact_path?: string;
  hyperparameters?: Record<string, unknown>;
  feature_names?: string[];
  is_active: boolean;
  is_experimental: boolean;
  registered_at: string;
  notes?: string;
}

export interface EvaluationRun {
  id: string;
  model_version_id: string;
  status: string;
  dataset_description?: string;
  num_samples?: number;
  num_positive?: number;
  num_negative?: number;
  accuracy?: number;
  precision?: number;
  recall?: number;
  f1_score?: number;
  macro_f1?: number;
  pr_auc?: number;
  roc_auc?: number;
  false_positive_rate?: number;
  confusion_matrix?: number[][];
  pr_curve_data?: { precision: number[]; recall: number[]; thresholds: number[] };
  roc_curve_data?: { fpr: number[]; tpr: number[] };
  notes?: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
}

export interface Investigation {
  id: string;
  transaction_id: string;
  status: string;
  priority: string;
  opened_by?: string;
  assigned_to?: string;
  opened_at: string;
  updated_at: string;
  amount?: number;
}

export interface AuditEvent {
  id: string;
  actor_email?: string;
  action: string;
  resource_type?: string;
  resource_id?: string;
  ip_address?: string;
  extra?: Record<string, unknown>;
  created_at: string;
}

// ── Client Factory ────────────────────────────────────────────────────────────

function createClient(): AxiosInstance {
  const client = axios.create({
    baseURL: "/api/v1",
    timeout: 30000,
    headers: { "Content-Type": "application/json" },
  });

  client.interceptors.request.use((config) => {
    const token = useAuthStore.getState().accessToken;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  });

  client.interceptors.response.use(
    (res) => res,
    async (error: AxiosError) => {
      if (error.response?.status === 401) {
        const refreshToken = useAuthStore.getState().refreshToken;
        if (refreshToken) {
          try {
            const res = await axios.post<TokenResponse>("/api/v1/auth/refresh", {
              refresh_token: refreshToken,
            });
            useAuthStore.getState().setTokens(res.data.access_token, res.data.refresh_token);
            if (error.config) {
              error.config.headers.Authorization = `Bearer ${res.data.access_token}`;
              return client(error.config);
            }
          } catch {
            useAuthStore.getState().logout();
            window.location.href = "/login";
          }
        } else {
          useAuthStore.getState().logout();
          window.location.href = "/login";
        }
      }
      return Promise.reject(error);
    }
  );

  return client;
}

export const apiClient = createClient();

// ── API Functions ─────────────────────────────────────────────────────────────

export const authApi = {
  login: (email: string, password: string) => {
    const formData = new URLSearchParams();
    formData.append("username", email);
    formData.append("password", password);
    return apiClient.post<TokenResponse>("/auth/login", formData, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
  },
  logout: (refreshToken: string) =>
    apiClient.post("/auth/logout", { refresh_token: refreshToken }),
  me: () => apiClient.get<UserInfo>("/auth/me"),
};

export const dashboardApi = {
  summary: () => apiClient.get<DashboardSummary>("/dashboard/summary"),
  volumeTrend: (days = 30) => apiClient.get<TimeSeriesPoint[]>(`/dashboard/volume-trend?days=${days}`),
  fraudTrend: (days = 30) => apiClient.get<TimeSeriesPoint[]>(`/dashboard/fraud-trend?days=${days}`),
  riskDistribution: () => apiClient.get<RiskDistribution>("/dashboard/risk-distribution"),
  recentAlerts: (limit = 10) => apiClient.get<RecentAlert[]>(`/dashboard/recent-alerts?limit=${limit}`),
  modelHealth: () => apiClient.get<ModelHealthStatus>("/dashboard/model-health"),
};

export const transactionsApi = {
  list: (params: Record<string, string | number | boolean | undefined>) =>
    apiClient.get<PaginatedResponse<TransactionListItem>>("/transactions", { params }),
  get: (id: string) => apiClient.get(`/transactions/${id}`),
};

export const predictionsApi = {
  single: (data: {
    features: Record<string, number>;
    transaction_id?: string;
  }) => apiClient.post<PredictionResult>("/predictions/single", data),
  get: (id: string) => apiClient.get<PredictionResult>(`/predictions/${id}`),
};

export const batchApi = {
  upload: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return apiClient.post<BatchJobStatus>("/batch/upload", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
  listJobs: (page = 1) => apiClient.get<PaginatedResponse<BatchJobStatus>>(`/batch/jobs?page=${page}`),
  getJob: (id: string) => apiClient.get<BatchJobStatus>(`/batch/jobs/${id}`),
};

export const modelsApi = {
  list: () => apiClient.get<ModelVersion[]>("/models"),
  get: (id: string) => apiClient.get<ModelVersion>(`/models/${id}`),
  activate: (id: string) => apiClient.put(`/models/${id}/activate`),
};

export const evaluationApi = {
  listRuns: () => apiClient.get<EvaluationRun[]>("/evaluation/runs"),
  getRun: (id: string) => apiClient.get<EvaluationRun>(`/evaluation/runs/${id}`),
  triggerRun: (description?: string) =>
    apiClient.post("/evaluation/runs", null, { params: { description } }),
};

export const investigationsApi = {
  list: (params?: Record<string, string | number | undefined>) =>
    apiClient.get<PaginatedResponse<Investigation>>("/investigations", { params }),
  get: (id: string) => apiClient.get(`/investigations/${id}`),
  open: (transaction_id: string, priority = "medium") =>
    apiClient.post("/investigations", null, { params: { transaction_id, priority } }),
  addEvent: (id: string, event_type: string, notes?: string, confirmed_label?: number) =>
    apiClient.post(`/investigations/${id}/events`, null, {
      params: { event_type, notes, confirmed_label },
    }),
};

export const auditApi = {
  list: (params?: Record<string, string | number | undefined>) =>
    apiClient.get<PaginatedResponse<AuditEvent>>("/audit", { params }),
};

export const usersApi = {
  list: (page = 1) => apiClient.get(`/users?page=${page}`),
  create: (data: { email: string; full_name: string; password: string; role: string }) =>
    apiClient.post("/users", data),
  update: (id: string, data: { full_name?: string; role?: string; is_active?: boolean }) =>
    apiClient.put(`/users/${id}`, data),
};

export const healthApi = {
  liveness: () => apiClient.get("/health"),
  readiness: () => apiClient.get("/health/ready"),
};

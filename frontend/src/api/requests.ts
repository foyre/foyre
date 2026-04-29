import type {
  Comment,
  HistoryEvent,
  IntakeRequest,
  RequestStatus,
} from "../types/domain";
import { request } from "./client";

export const listRequests = () => request<IntakeRequest[]>("/requests");

export const getRequest = (id: number) =>
  request<IntakeRequest>(`/requests/${id}`);

export const createRequest = (payload: Record<string, unknown>) =>
  request<IntakeRequest>("/requests", {
    method: "POST",
    body: JSON.stringify({ payload }),
  });

export const updateRequest = (id: number, payload: Record<string, unknown>) =>
  request<IntakeRequest>(`/requests/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ payload }),
  });

export const submitRequest = (id: number) =>
  request<IntakeRequest>(`/requests/${id}/submit`, { method: "POST" });

export const changeStatus = (id: number, new_status: RequestStatus) =>
  request<IntakeRequest>(`/requests/${id}/status`, {
    method: "POST",
    body: JSON.stringify({ new_status }),
  });

export const listComments = (id: number) =>
  request<Comment[]>(`/requests/${id}/comments`);

export const addComment = (id: number, body: string) =>
  request<Comment>(`/requests/${id}/comments`, {
    method: "POST",
    body: JSON.stringify({ body }),
  });

export const getHistory = (id: number) =>
  request<HistoryEvent[]>(`/requests/${id}/history`);

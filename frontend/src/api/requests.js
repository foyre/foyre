import { request } from "./client";
export const listRequests = () => request("/requests");
export const getRequest = (id) => request(`/requests/${id}`);
export const createRequest = (payload) => request("/requests", {
    method: "POST",
    body: JSON.stringify({ payload }),
});
export const updateRequest = (id, payload) => request(`/requests/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ payload }),
});
export const submitRequest = (id) => request(`/requests/${id}/submit`, { method: "POST" });
export const changeStatus = (id, new_status) => request(`/requests/${id}/status`, {
    method: "POST",
    body: JSON.stringify({ new_status }),
});
export const listComments = (id) => request(`/requests/${id}/comments`);
export const addComment = (id, body) => request(`/requests/${id}/comments`, {
    method: "POST",
    body: JSON.stringify({ body }),
});
export const getHistory = (id) => request(`/requests/${id}/history`);

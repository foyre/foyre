import type { User } from "../types/domain";
import { request } from "./client";

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export function login(username: string, password: string) {
  return request<LoginResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export function me() {
  return request<User>("/auth/me");
}

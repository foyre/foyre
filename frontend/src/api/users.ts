import type { Role, User } from "../types/domain";
import { request } from "./client";

export function changeMyPassword(currentPassword: string, newPassword: string) {
  return request<User>("/users/me/password", {
    method: "POST",
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  });
}

export function listUsers() {
  return request<User[]>("/admin/users");
}

export interface CreateUserInput {
  username: string;
  email: string;
  password: string;
  role: Role;
  must_change_password?: boolean;
}

export function createUser(input: CreateUserInput) {
  return request<User>("/admin/users", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export interface UpdateUserInput {
  role?: Role;
  is_active?: boolean;
}

export function updateUser(id: number, patch: UpdateUserInput) {
  return request<User>(`/admin/users/${id}`, {
    method: "PATCH",
    body: JSON.stringify(patch),
  });
}

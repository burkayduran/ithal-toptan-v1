"use client";

import { useState, useMemo } from "react";
import {
  useAdminCategories,
  useCreateCategory,
  useUpdateCategory,
  useDeleteCategory,
} from "@/features/admin/hooks";
import type { AdminCategory } from "@/features/admin/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2, Plus, Pencil, Trash2, X, Check } from "lucide-react";

function slugify(s: string) {
  return s
    .toLowerCase()
    .trim()
    .replace(/\s+/g, "-")
    .replace(/[^a-z0-9-]/g, "");
}

interface EditState {
  id: string;
  name: string;
  slug: string;
  gumruk_rate: string;
  sort_order: string;
}

/** Build a tree-ordered flat list: parent first, then children (indented). */
function buildTreeList(categories: AdminCategory[]): (AdminCategory & { depth: number })[] {
  const roots = categories.filter((c) => !c.parent_id);
  const childrenMap = new Map<string, AdminCategory[]>();
  for (const c of categories) {
    if (c.parent_id) {
      const siblings = childrenMap.get(c.parent_id) ?? [];
      siblings.push(c);
      childrenMap.set(c.parent_id, siblings);
    }
  }

  const result: (AdminCategory & { depth: number })[] = [];
  for (const root of roots) {
    result.push({ ...root, depth: 0 });
    const children = childrenMap.get(root.id) ?? [];
    for (const child of children) {
      result.push({ ...child, depth: 1 });
    }
  }

  // Add orphans (parent_id set but parent not found)
  const addedIds = new Set(result.map((r) => r.id));
  for (const c of categories) {
    if (!addedIds.has(c.id)) {
      result.push({ ...c, depth: 1 });
    }
  }

  return result;
}

/** Build a select option list with indent for sub-categories. */
function buildParentOptions(categories: AdminCategory[], excludeId?: string) {
  const roots = categories.filter((c) => !c.parent_id && c.id !== excludeId);
  return roots.map((r) => ({ id: r.id, label: r.name }));
}

export default function AdminCategoriesPage() {
  const { data: categories, isLoading, isError, refetch } = useAdminCategories();
  const { mutate: create, isPending: isCreating } = useCreateCategory();
  const { mutate: update, isPending: isUpdating } = useUpdateCategory();
  const { mutate: remove, isPending: isDeleting, variables: deletingId } = useDeleteCategory();

  const [newForm, setNewForm] = useState({ name: "", slug: "", gumruk_rate: "", sort_order: "0", parent_id: "" });
  const [editState, setEditState] = useState<EditState | null>(null);
  const [createError, setCreateError] = useState("");

  const treeList = useMemo(() => buildTreeList(categories ?? []), [categories]);
  const parentOptions = useMemo(() => buildParentOptions(categories ?? []), [categories]);

  function handleNameChange(name: string) {
    setNewForm((prev) => ({ ...prev, name, slug: slugify(name) }));
  }

  function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setCreateError("");
    if (!newForm.name.trim() || !newForm.slug.trim()) return;
    create(
      {
        name: newForm.name.trim(),
        slug: newForm.slug.trim(),
        parent_id: newForm.parent_id || undefined,
        gumruk_rate: newForm.gumruk_rate ? parseFloat(newForm.gumruk_rate) / 100 : undefined,
        sort_order: parseInt(newForm.sort_order) || 0,
      },
      {
        onSuccess: () => setNewForm({ name: "", slug: "", gumruk_rate: "", sort_order: "0", parent_id: "" }),
        onError: (err) => setCreateError((err as Error).message),
      }
    );
  }

  function startEdit(cat: AdminCategory) {
    setEditState({
      id: cat.id,
      name: cat.name,
      slug: cat.slug,
      gumruk_rate: cat.gumruk_rate != null ? String(Math.round(cat.gumruk_rate * 100)) : "",
      sort_order: String(cat.sort_order),
    });
  }

  function cancelEdit() {
    setEditState(null);
  }

  function handleUpdate() {
    if (!editState) return;
    update(
      {
        id: editState.id,
        payload: {
          name: editState.name.trim() || undefined,
          slug: editState.slug.trim() || undefined,
          gumruk_rate:
            editState.gumruk_rate !== "" ? parseFloat(editState.gumruk_rate) / 100 : undefined,
          sort_order: parseInt(editState.sort_order) || 0,
        },
      },
      { onSuccess: () => setEditState(null) }
    );
  }

  return (
    <div className="p-6 max-w-3xl">
      <h1 className="text-xl font-bold text-gray-900 mb-6">Kategoriler</h1>

      {/* Create form */}
      <form
        onSubmit={handleCreate}
        className="bg-white border border-gray-200 rounded-xl p-5 mb-6 space-y-4"
      >
        <h2 className="text-sm font-semibold text-gray-900 flex items-center gap-1.5">
          <Plus className="h-4 w-4 text-blue-600" />
          Yeni Kategori
        </h2>
        <div className="grid sm:grid-cols-2 gap-3">
          <div className="space-y-1">
            <Label className="text-xs">Ad *</Label>
            <Input
              required
              value={newForm.name}
              onChange={(e) => handleNameChange(e.target.value)}
              placeholder="Elektronik"
            />
          </div>
          <div className="space-y-1">
            <Label className="text-xs">Slug *</Label>
            <Input
              required
              value={newForm.slug}
              onChange={(e) => setNewForm((p) => ({ ...p, slug: e.target.value }))}
              placeholder="elektronik"
            />
          </div>
          <div className="space-y-1">
            <Label className="text-xs">Üst Kategori</Label>
            <select
              value={newForm.parent_id}
              onChange={(e) => setNewForm((p) => ({ ...p, parent_id: e.target.value }))}
              className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 bg-white focus:outline-none"
            >
              <option value="">Ana Kategori (yok)</option>
              {parentOptions.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-1">
            <Label className="text-xs">Gümrük Oranı (%)</Label>
            <Input
              type="number"
              step="0.1"
              min="0"
              max="200"
              value={newForm.gumruk_rate}
              onChange={(e) => setNewForm((p) => ({ ...p, gumruk_rate: e.target.value }))}
              placeholder="35"
            />
          </div>
          <div className="space-y-1">
            <Label className="text-xs">Sıralama</Label>
            <Input
              type="number"
              min="0"
              value={newForm.sort_order}
              onChange={(e) => setNewForm((p) => ({ ...p, sort_order: e.target.value }))}
            />
          </div>
        </div>
        {createError && (
          <p className="text-xs text-red-600 bg-red-50 rounded px-3 py-2">{createError}</p>
        )}
        <Button type="submit" size="sm" disabled={isCreating}>
          {isCreating ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : "Ekle"}
        </Button>
      </form>

      {/* List */}
      {isLoading ? (
        <div className="text-sm text-gray-400 py-10 text-center">Yükleniyor...</div>
      ) : isError ? (
        <div className="text-sm text-red-500 py-10 text-center">
          Hata.{" "}
          <button className="underline" onClick={() => refetch()}>
            Tekrar dene
          </button>
        </div>
      ) : treeList.length === 0 ? (
        <div className="text-sm text-gray-400 py-10 text-center">Henüz kategori yok.</div>
      ) : (
        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-600">Ad / Slug</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-600 hidden sm:table-cell">Gümrük</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-600 hidden md:table-cell">Sıra</th>
                <th className="text-right px-4 py-3 text-xs font-medium text-gray-600">İşlem</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {treeList.map((cat) => {
                const isEditing = editState?.id === cat.id;
                return (
                  <tr key={cat.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      {isEditing ? (
                        <div className="space-y-1.5">
                          <Input
                            value={editState.name}
                            onChange={(e) =>
                              setEditState((s) => s && { ...s, name: e.target.value })
                            }
                            className="h-7 text-xs"
                          />
                          <Input
                            value={editState.slug}
                            onChange={(e) =>
                              setEditState((s) => s && { ...s, slug: e.target.value })
                            }
                            className="h-7 text-xs font-mono"
                          />
                        </div>
                      ) : (
                        <div style={{ paddingLeft: cat.depth * 24 }}>
                          <p className="font-medium text-gray-900">
                            {cat.depth > 0 && <span className="text-gray-300 mr-1">—</span>}
                            {cat.name}
                          </p>
                          <p className="text-xs text-gray-400 font-mono">{cat.slug}</p>
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3 text-gray-600 hidden sm:table-cell">
                      {isEditing ? (
                        <Input
                          type="number"
                          step="0.1"
                          min="0"
                          value={editState.gumruk_rate}
                          onChange={(e) =>
                            setEditState((s) => s && { ...s, gumruk_rate: e.target.value })
                          }
                          className="h-7 text-xs w-20"
                        />
                      ) : cat.gumruk_rate != null ? (
                        `%${Math.round(cat.gumruk_rate * 100)}`
                      ) : (
                        "—"
                      )}
                    </td>
                    <td className="px-4 py-3 text-gray-600 hidden md:table-cell">
                      {isEditing ? (
                        <Input
                          type="number"
                          min="0"
                          value={editState.sort_order}
                          onChange={(e) =>
                            setEditState((s) => s && { ...s, sort_order: e.target.value })
                          }
                          className="h-7 text-xs w-16"
                        />
                      ) : (
                        cat.sort_order
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        {isEditing ? (
                          <>
                            <Button
                              size="sm"
                              variant="ghost"
                              className="h-7 w-7 p-0"
                              onClick={handleUpdate}
                              disabled={isUpdating}
                            >
                              {isUpdating ? (
                                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                              ) : (
                                <Check className="h-3.5 w-3.5 text-green-600" />
                              )}
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              className="h-7 w-7 p-0"
                              onClick={cancelEdit}
                            >
                              <X className="h-3.5 w-3.5" />
                            </Button>
                          </>
                        ) : (
                          <>
                            <Button
                              size="sm"
                              variant="ghost"
                              className="h-7 w-7 p-0"
                              onClick={() => startEdit(cat)}
                            >
                              <Pencil className="h-3.5 w-3.5 text-gray-500" />
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              className="h-7 w-7 p-0"
                              onClick={() => remove(cat.id)}
                              disabled={isDeleting && deletingId === cat.id}
                            >
                              {isDeleting && deletingId === cat.id ? (
                                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                              ) : (
                                <Trash2 className="h-3.5 w-3.5 text-red-400" />
                              )}
                            </Button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

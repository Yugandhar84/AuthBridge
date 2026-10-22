"use client";

import { useEffect, useState } from "react";
import { get, provider } from "./api";
import type { CatalogItem, Practitioner } from "./types";

export type ClinicContext = {
  organization: { name: string };
  practitioners: Practitioner[];
  catalog: CatalogItem[];
  diagnoses: { code: string; display: string }[];
  backend: string;
  ai: string;
};

const KEY = "authbridge.practitioner";

export function useClinic() {
  const [ctx, setCtx] = useState<ClinicContext | null>(null);
  const [practitionerId, setPractitionerIdState] = useState<string>("pr-patel");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    try {
      const saved = window.localStorage.getItem(KEY);
      if (saved) setPractitionerIdState(saved);
    } catch {
      /* storage unavailable; keep default */
    }
    get<ClinicContext>(provider("/api/context")).then(setCtx).catch((e) => setError(e.message));
  }, []);

  const setPractitionerId = (id: string) => {
    setPractitionerIdState(id);
    try {
      window.localStorage.setItem(KEY, id);
    } catch {
      /* ignore */
    }
  };

  const practitioner = ctx?.practitioners.find((p) => p.practitioner_role_id === practitionerId);
  return { ctx, practitioner, practitionerId, setPractitionerId, error };
}

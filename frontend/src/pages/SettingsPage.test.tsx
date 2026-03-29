import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import * as api from "@/lib/api";
import { SettingsPage } from "./SettingsPage";

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    fetchAdminSettings: vi.fn(),
    patchAdminSettings: vi.fn(),
  };
});

const baseSettings: api.AdminSettings = {
  server_label: "lab",
  default_download_duration_sec: 10,
  default_upload_duration_sec: 10,
  default_parallel_streams: 4,
  default_payload_bytes: 16_777_216,
  default_ping_samples: 30,
  default_warmup_ping_samples: 5,
  retention_days: null,
  allow_client_self_label: true,
  allow_network_label: true,
  anomaly_baseline_runs: 20,
  anomaly_deviation_percent: 25,
  download_max_bytes: 1_000_000_000,
  upload_max_bytes: 1_000_000_000,
};

beforeEach(() => {
  vi.mocked(api.fetchAdminSettings).mockResolvedValue({ ...baseSettings });
  vi.mocked(api.patchAdminSettings).mockImplementation(async (patch) => ({
    ...baseSettings,
    ...patch,
  } as api.AdminSettings));
});

describe("SettingsPage", () => {
  it("loads settings and submits save", async () => {
    render(<SettingsPage />);
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /^save$/i })).toBeInTheDocument(),
    );
    fireEvent.click(screen.getByRole("button", { name: /^save$/i }));
    await waitFor(() => expect(api.patchAdminSettings).toHaveBeenCalled());
    await waitFor(() =>
      expect(screen.getByRole("status")).toHaveTextContent(/saved successfully/i),
    );
  });
});

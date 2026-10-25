export async function predict(params: {
  healthOutcome: string;
  longitude: number;
  latitude: number;
  image: File;
}) {
  const query = new URLSearchParams({
    health_outcome: params.healthOutcome,
    longitude: String(params.longitude),
    latitude: String(params.latitude),
  });

  const formData = new FormData();
  formData.append("image", params.image);

  const res = await fetch(`/api/predict?${query.toString()}`, {
    method: "POST",
    headers: { accept: "application/json" },
    body: formData,
  });

  if (!res.ok) {
    let message = `API error: ${res.status}`;

    try {
      const contentType = res.headers.get("content-type") ?? "";
      if (contentType.includes("application/json")) {
        const errorBody = await res.json();
        message = errorBody.error ?? message;
      } else {
        const text = await res.text();
        if (text) message = text;
      }
    } catch (err) {
      console.error("Failed to parse error response body:", err);
    }

    throw new Error(message);
  }

  return res.json();
}

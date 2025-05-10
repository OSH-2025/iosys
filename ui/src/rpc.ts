import { errorMessage } from "./states";

const BASE_URL = "http://localhost:8000";

export default {
  chat: defineApi<{ input: string }, { response: string }>("/chat"),
};

function defineApi<Request, Response>(endpoint: string) {
  return async (request: Request): Promise<Response> => {
    try {
      const response = await fetch(BASE_URL + endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        errorMessage.value = `Error: ${response.status} ${response.statusText}`;
        throw new Error(errorMessage.value);
      }

      return await response.json();
    } catch (error) {
      errorMessage.value = `${error}`;
      throw error;
    }
  };
}

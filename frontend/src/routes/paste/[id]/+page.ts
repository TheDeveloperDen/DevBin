import { genRandomContent } from "$lib/generateRandomText";
import { wordList } from "./words";

export async function load({ params }) {
  const { id } = params;

  const content = genRandomContent(id);
  return {
    title: `Paste #${id}`,
    created_at: Date(),
    content: content,
    expires_at: Date(),
  };
}

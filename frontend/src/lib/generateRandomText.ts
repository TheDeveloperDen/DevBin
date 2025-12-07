import seedrandom from "seedrandom";
import { wordList } from "../routes/paste/[id]/words";

export const genRandomContent = (seed: string | number) => {
  const rng = seedrandom(String(seed));
  let content = "";
  const length = Math.floor(rng() * 1000 + 100);
  for (var i = 0; i < length; i++) {
    const word = wordList[Math.floor(rng() * wordList.length)];
    content += " " + word;
  }
  return content;
};

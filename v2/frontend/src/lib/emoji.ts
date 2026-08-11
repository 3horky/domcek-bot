import { Categories } from 'emoji-picker-react'

export const carloEmojiCategories = [
  { category: Categories.SUGGESTED, name: 'Nedávne' },
  { category: Categories.CUSTOM, name: 'Emoji servera' },
  { category: Categories.SMILEYS_PEOPLE, name: 'Ľudia a úsmevy' },
  { category: Categories.ANIMALS_NATURE, name: 'Zvieratá a príroda' },
  { category: Categories.FOOD_DRINK, name: 'Jedlo a nápoje' },
  { category: Categories.TRAVEL_PLACES, name: 'Cestovanie a miesta' },
  { category: Categories.ACTIVITIES, name: 'Aktivity' },
  { category: Categories.OBJECTS, name: 'Predmety' },
  { category: Categories.SYMBOLS, name: 'Symboly' },
  { category: Categories.FLAGS, name: 'Vlajky' },
]

export function discordEmojiUrl(id: string, animated = false) {
  return `https://cdn.discordapp.com/emojis/${id}.${animated ? 'gif' : 'webp'}?size=64&quality=lossless`
}

export type Restaurant = {
    name: string;
    reason: string;
    maps_link: string;
    photo_urls?: string[];
  };
  
export type RevealData = {
    personality_lines: Record<string, string>;
    agreements: string;
    conflicts: string;
    primary: Restaurant;
    backups: Restaurant[];
  };

/**
 * Persist a participant display name for a session in sessionStorage.
 *
 * @param code - Session code; normalized to uppercase in the storage key.
 * @param name - Participant name to store.
 */
export function saveParticipantName(code: string, name: string) {
    sessionStorage.setItem(`up2u:${code.toUpperCase()}:name`, name);
  }

/**
 * Read the stored participant name for a session.
 *
 * @param code - Session code; normalized to uppercase in the storage key.
 * @returns The stored name, or null if none is saved.
 */
export function getParticipantName(code: string){
    return sessionStorage.getItem(`up2u:${code.toUpperCase()}:name`)
}

/**
 * Persist reveal payload for a session in sessionStorage.
 *
 * @param code - Session code; normalized to uppercase in the storage key.
 * @param reveal - Parsed reveal data from the backend or WebSocket.
 */
export function saveReveal(code: string, reveal: RevealData){
    sessionStorage.setItem(`up2u:${code.toUpperCase()}:reveal`, JSON.stringify(reveal))
}

/**
 * Read stored reveal data for a session.
 *
 * @param code - Session code; normalized to uppercase in the storage key.
 * @returns Parsed reveal data, or undefined if none is saved.
 */
export function getReveal(code: string){
    const reveal = sessionStorage.getItem(`up2u:${code.toUpperCase()}:reveal`)
    if (!reveal){
        return
    }
    return JSON.parse(reveal) as RevealData;
}

/**
 * Remove stored reveal data for a session.
 *
 * @param code - Session code; normalized to uppercase in the storage key.
 */
export function clearReveal(code: string){
    sessionStorage.removeItem(`up2u:${code.toUpperCase()}:reveal`);
}

export type SurveyDraft = {
    step: number;
    hunger: number;
    vibe: string;
    cuisinesRanked: string[];
    travelDistance: string;
    dietary: string[];
};

/**
 * Persist in-progress survey answers for a session.
 *
 * @param code - Session code; normalized to uppercase in the storage key.
 * @param draft - Current survey step and answer fields.
 */
export function saveDraft(code: string, draft: SurveyDraft) {
    sessionStorage.setItem(
        `up2u:${code.toUpperCase()}:draft`,
        JSON.stringify(draft),
    );
}

/**
 * Read stored survey draft for a session.
 *
 * @param code - Session code; normalized to uppercase in the storage key.
 * @returns Parsed draft, or undefined if none is saved.
 */
export function getDraft(code: string) {
    const draft = sessionStorage.getItem(`up2u:${code.toUpperCase()}:draft`);
    if (!draft) {
        return;
    }
    return JSON.parse(draft) as SurveyDraft;
}

/**
 * Remove stored survey draft for a session.
 *
 * @param code - Session code; normalized to uppercase in the storage key.
 */
export function clearDraft(code: string) {
    sessionStorage.removeItem(`up2u:${code.toUpperCase()}:draft`);
}

/**
 * Store a one-time flash message shown on the home page after redirect.
 *
 * @param message - User-facing message written to sessionStorage key up2u:message.
 */
export function setFlashMessage(message: string) {
    sessionStorage.setItem("up2u:message", message);
}
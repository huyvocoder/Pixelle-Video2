# Copyright (C) 2025 AIDC-AI
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Image prompt generation template

For generating image prompts from narrations.
"""

import json
from typing import List, Optional


# ==================== PRESET IMAGE STYLES ====================
# Predefined visual styles for different use cases

IMAGE_STYLE_PRESETS = {
    "stick_figure": {
        "name": "Stick Figure Sketch",
        "description": "stick figure style sketch, black and white lines, pure white background, minimalist hand-drawn feel",
        "use_case": "General scenes, simple and intuitive"
    },
    
    "minimal": {
        "name": "Minimalist Abstract",
        "description": "minimalist abstract art, geometric shapes, clean composition, modern design, soft pastel colors",
        "use_case": "Modern, artistic feel"
    },
    
    "concept": {
        "name": "Conceptual Visual",
        "description": "conceptual visual metaphors, symbolic elements, thought-provoking imagery, artistic interpretation",
        "use_case": "Deep content, philosophical thinking"
    },
}

# Default preset
DEFAULT_IMAGE_STYLE = "stick_figure"


IMAGE_PROMPT_GENERATION_PROMPT = """# Role Definition
You are a visual director creating prompts for a modern AI illustration model (flat 2D vector style, similar to explainer-video characters). This model handles camera framing, natural expressions, and multiple characters well - so unlike a bare-bones sketch model, you should actively direct the SHOT, POSE, and EXPRESSION, not just name an object.

# Core Task
Based on the video script, create one **English** image prompt for each narration line. Each prompt must describe: (1) a camera/shot type, (2) the subject's pose and facial expression matching the narration's emotional tone, (3) any object(s) they interact with, and (4) if there is more than one character, an explicit spatial-separation rule so limbs/objects never overlap between characters.

**Important: The input contains {narrations_count} narrations. You must generate one corresponding image prompt for each narration, totaling {narrations_count} image prompts.**

# Input Content
{narrations_json}

# Output Requirements

## Image Prompt Specifications (STRICT)
- Language: **Must use English** (for AI image generation models)
- Length: **{min_words}-{max_words} English words.**
- Do NOT add general art-style words (flat/minimalist/vector/etc.) - that is handled separately by a fixed style prefix. Focus only on shot, pose, expression, and objects.

## 1. Choose a camera/shot type that fits the narration
Pick whichever best matches the moment - vary it across scenes, don't repeat the same shot every time:
- `full body shot` - for actions, movement, showing an object at their feet, multiple people
- `close-up half-body shot` / `close-up portrait shot` - for strong emotional beats, reactions
- `three-quarter angle shot` - for someone at a desk, thinking, working

## 2. Match pose + expression to the narration's emotion
Every prompt should specify a simple, clear facial expression and body language appropriate to the line - e.g. "worried panicked expression, wide eyes", "thoughtful expression, chin resting on hand", "big genuine laughing smile, eyes closed happily", "confident relaxed posture". Do not leave expression generic/neutral unless the narration is genuinely neutral.

## 3. Objects: describe naturally, keep ownership unambiguous
If the character holds or uses an object, say so plainly (e.g. "holding a cup of coffee", "counting a stack of paper money", "pointing at a rising bar chart on a whiteboard"). No need for extra qualifiers when there's only one character.

## 4. NEVER put readable text, numbers, or logos anywhere in the image
This image model cannot render legible text under any circumstances - it always comes out as garbled, misspelled, or nonsense characters, no matter how short. This applies to EVERYTHING: signs, labels, book/shop titles, calendar dates, clock/counter digits, price tags, screens, packaging, banners - anything a viewer would try to "read".
- If the narration mentions something with text on it (a sign, a date, a price, a title), depict the OBJECT ITSELF without any text on it, or replace it with a wordless symbolic equivalent - e.g. "a calendar with one date circled in red" (no visible numbers), "a blank price tag on a string" (no digits), "a closed book with a plain cover" (no title), "a glowing exclamation mark" instead of a warning label.
- Never write phrases like "a sign reading X", "text saying Y", "a label with the word Z" in the prompt - the model will always render this wrong and it looks broken in the final video.
- The narration/voice-over already conveys the specific words, numbers, or names - the image only needs to convey the concept visually, not spell it out.

## 5. Rigid elongated objects (rackets, bats, poles, umbrellas, swords, canes) must stay straight
These objects are prone to appearing bent or broken where they meet the hand/body. When such an object appears, explicitly describe it as straight and held naturally, e.g. "holding a badminton racket with its straight shaft extended forward" rather than just "holding a racket". This reduces (does not eliminate) the bending artifact.

## 5b. Keep hand poses and gestures simple
Hands are the single hardest thing for this model to render correctly - the more complex the gesture, the higher the error rate. Prefer simple, common poses: one hand holding an object at the side, arms relaxed, a simple wave, hands resting on a desk/lap. AVOID describing intricate multi-finger gestures, both hands intertwined or clasped together, hands near the face/neck, or hands overlapping each other - these consistently produce malformed results. If the narration implies a complex gesture, simplify it to the closest simple equivalent (e.g. "hands clasped together" -> "hands resting together on the desk"). MANDATORY in every single prompt where a hand is described or implied (holding, pointing, gesturing, fists, waving - not just close-ups): include the exact phrase "simple rounded mitten-like hand(s), no individual visible fingers". This is a hard style-consistency requirement, not a case-by-case judgment call - apply it every time, even for a distant/full-body shot.

## 6. Multiple characters: ALWAYS add explicit spatial separation
If a scene needs 2 or more people, you MUST include this pattern (adapt the count/positions):
"N people standing far apart in their own separate space with large empty gaps between them, person on the left doing X, person on the right doing Y, each item held close to that person's own body only, not extending into neighboring person's space"
This is mandatory whenever more than one character appears - it is what prevents the model from blending limbs/objects between characters.

## 7. Keep everything minimal - this is the priority style now
The target style is an extremely minimal glowing round-head character with simple dot eyes and a plain simple body, similar to a friendly notion-style icon. Backgrounds must stay minimal too - a plain muted color background with AT MOST one or two simple symbolic props relevant to the scene (a book, a tree, a chair, a dumbbell) - never describe detailed rooms, furniture sets, or busy environments. The simpler the scene, the more reliably it renders and the faster it generates - prefer removing detail over adding it whenever in doubt.

## 8. Distinguishing multiple different characters across scenes
When the story has more than one named/recurring character (e.g. a protagonist and a supporting character), do NOT redesign their whole look - keep the same minimal round-head base for both. Distinguish them with ONE small accessory difference only, consistently reused for that character every time they appear - e.g. "with a small tuft of hair", "wearing round glasses", "with a small mustache", "wearing a tiny hat". Do not invent a new accessory each scene - pick one per character and repeat it.

## 9. Character scenes MUST include the character description yourself - it is not added automatically
Unlike some setups, the fixed style prefix applied to every prompt is STYLE-ONLY (line weight, colors, background rules) - it does NOT describe what the character looks like. So for every scene that has a character, you must explicitly include this exact phrase as part of your prompt: "glowing round-head character, simple black dot eyes, plain thin simple body and limbs, thin uniform-width limbs the same thickness top to bottom, simple oval feet". Do not paraphrase or alter this phrase, and do not invent a different hand/body/leg shape, mouth, or proportions for a specific scene - only vary the pose, camera angle/shot type, expression (via eyes/eyebrows/mouth curve - not by adding/removing the mouth itself), and object interaction. Consistency of the base design across every scene is more important than any single scene's creativity.

## 10. B-roll: not every scene needs a character
Some scenes work better as a pure symbolic/b-roll shot - a single object or simple visual metaphor with NO character at all (e.g. just a glowing lightbulb, a calendar with a date circled, a stack of coins, an alarm clock) - especially for scenes about abstract concepts, statistics, time passing, or transitions between story beats. Mix character scenes with occasional b-roll scenes where it fits naturally; do not force a character into every single scene. When a scene is b-roll: describe ONLY the object/symbol, keep it equally minimal (same soft muted background, at most one object), and do NOT include the character phrase from rule 9 (or any character/person/hand/limb/leg wording) anywhere in the prompt - the fixed style prefix is character-agnostic, so nothing else will silently add a character in. A b-roll prompt that leaks in character wording is a bug in your output, not a style choice.

## 10b. Keep b-roll concepts literal and simple - avoid abstract visual metaphors
This model draws literal objects reliably; it struggles badly with conceptual/metaphorical visuals. AVOID prompts like "a coin melting like ice", "a transparent shield offering no real protection", "an icon sinking downward symbolizing devaluation", "a maze icon representing confusion" - these describe an idea, not a concrete image, and consistently render as confused, muddled, or nonsensical output. Instead, pick ONE simple, literal, static object or scene that visually implies the idea without needing melting/sinking/transforming action or invisible/intangible qualities: e.g. instead of "a coin melting like ice" use "a single gold coin with a crack down the middle"; instead of "a transparent shield offering no protection" use "a person flinching behind a small cracked shield"; instead of "an icon sinking symbolizing devaluation" use "a stack of coins with a downward red arrow next to it". If you can't picture the exact static frame a camera would capture, simplify the concept further until you can.

## Good Examples (this is the target quality/format)
- "close-up half-body portrait shot of one person, worried panicked expression, wide eyes, hand touching forehead, holding a thermometer in the other hand"
- "three-quarter angle shot of one person sitting at a desk, chin resting on hand, thoughtful expression, laptop open showing a simple rising chart, question mark symbol floating above their head"
- "2 people standing far apart in their own separate space with large empty gaps between them, person on left holding a stack of paper money close to their own body, person on right pointing at a rising bar chart on a whiteboard, each item held close to that person's own body only"

# Output Format
Strictly output in the following JSON format, **image prompts must be in English**:

```json
{{
  "image_prompts": [
    "[English image prompt: shot type + pose/expression + object, {min_words}-{max_words} words]",
    "[English image prompt: shot type + pose/expression + object, {min_words}-{max_words} words]"
  ]
}}
```

# Important Reminders
1. Only output JSON format content, do not add any explanations
2. Ensure JSON format is strictly correct and can be directly parsed by the program
3. Input is {{"narrations": [narration array]}} format, output is {{"image_prompts": [image prompt array]}} format
4. **The output image_prompts array must contain exactly {narrations_count} elements, corresponding one-to-one with the input narrations array**
5. **Image prompts must use English** and be **{min_words}-{max_words} words each**
6. Vary shot types across the scenes - do not use the same camera angle for every single scene
7. Every prompt needs a clear expression/pose - avoid generic "standing there" descriptions
8. Any scene with 2+ characters MUST use the spatial-separation pattern from rule 6 above

Now, please create {narrations_count} corresponding **English** image prompts for the above {narrations_count} narrations, each following the shot/pose/expression/object structure above. Only output JSON, no other content.
"""


def build_image_prompt_prompt(
    narrations: List[str],
    min_words: int,
    max_words: int
) -> str:
    """
    Build image prompt generation prompt
    
    Note: Style/prefix will be applied later via prompt_prefix in config.
    
    Args:
        narrations: List of narrations
        min_words: Minimum word count
        max_words: Maximum word count
    
    Returns:
        Formatted prompt for LLM
    
    Example:
        >>> build_image_prompt_prompt(narrations, 50, 100)
    """
    narrations_json = json.dumps(
        {"narrations": narrations},
        ensure_ascii=False,
        indent=2
    )
    
    return IMAGE_PROMPT_GENERATION_PROMPT.format(
        narrations_json=narrations_json,
        narrations_count=len(narrations),
        min_words=min_words,
        max_words=max_words
    )


import { useMapsLibrary } from "@vis.gl/react-google-maps";

interface Props {
  onPlaceSelect: (place: google.maps.places.Place | null) => void;
}

/**
 * Google Places autocomplete input for selecting a session location.
 *
 * @param onPlaceSelect - Callback invoked with the selected place or null.
 * @returns gmp-place-autocomplete custom element wrapper.
 */
export const LocationAutocomplete = ({ onPlaceSelect }: Props) => {
  // make sure the `<gmp-place-autocomplete>` component gets loaded
  useMapsLibrary("places");

  /**
   * Fetch place fields and notify the parent of the selection.
   *
   * @param place - Google Places Place object from autocomplete selection.
   */
  async function handlePlaceSelect(place: google.maps.places.Place) {
    await place.fetchFields({
      fields: ["displayName", "formattedAddress", "location"]
    });

    onPlaceSelect(place);
  }

  // Note: This is a React 19 thing to be able to treat custom elements this way.
  //   In React before v19, you'd have to use a ref, or use the PlaceAutocompleteElement
  //   constructor instead.
  return (
    <div className="autocomplete-container">
      <gmp-place-autocomplete
        ongmp-select={(event: google.maps.places.PlacePredictionSelectEvent) =>
          void handlePlaceSelect(event.placePrediction.toPlace())
        }
      />
    </div>
  );
};

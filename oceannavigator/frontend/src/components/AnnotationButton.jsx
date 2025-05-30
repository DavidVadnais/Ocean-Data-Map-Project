import React from "react";
import { Button, OverlayTrigger, Tooltip } from "react-bootstrap";

import { faPencil } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";

import { withTranslation } from "react-i18next";

function AnnotationButton(props) {
  const handleAnnotation = () => {
    props.updateUI({ modalType: "annotation", showModal: true });
  };

  return (
    <OverlayTrigger
      key="annotation-overlay"
      placement="bottom"
      overlay={
        <Tooltip id={"annotation-tooltip"}>{__("Add Map Annotation")}</Tooltip>
      }
    >
      <Button onClick={handleAnnotation} className="annotation-button">
        <FontAwesomeIcon icon={faPencil} />
      </Button>
    </OverlayTrigger>
  );
}

export default withTranslation()(AnnotationButton);

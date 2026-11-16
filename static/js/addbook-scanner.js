(() => {
 const modal=document.getElementById('accScannerModal'), video=document.getElementById('accVideo');
 const field=document.getElementById('accField');let reader=null,controls=null;
 function close(){if(controls){controls.stop();controls=null;}if(reader){reader.reset();reader=null;}modal.hidden=true;}
 document.getElementById('scanAccButton').addEventListener('click',async()=>{
  modal.hidden=false;
  if(!window.ZXing){alert('Barcode engine did not load. Check internet access or type the printed ACC.NO manually.');return;}
  try{
   const formats=[ZXing.BarcodeFormat.CODE_128,ZXing.BarcodeFormat.CODE_39,ZXing.BarcodeFormat.EAN_13,ZXing.BarcodeFormat.EAN_8,ZXing.BarcodeFormat.ITF,ZXing.BarcodeFormat.CODABAR,ZXing.BarcodeFormat.UPC_A,ZXing.BarcodeFormat.UPC_E];
   const hints=new Map();hints.set(ZXing.DecodeHintType.POSSIBLE_FORMATS,formats);hints.set(ZXing.DecodeHintType.TRY_HARDER,true);
   reader=new ZXing.BrowserMultiFormatReader(hints,300);
   controls=await reader.decodeFromConstraints({audio:false,video:{facingMode:{ideal:'environment'}}},video,(decoded)=>{
    if(decoded){field.value=decoded.getText().trim();close();}
   });
  }catch(err){alert('Camera could not start. Allow permission and use localhost/HTTPS. '+err.message);}
 });
 document.getElementById('closeAccScanner').addEventListener('click',close);
 document.getElementById('stopAccScanner').addEventListener('click',close);
})();

(() => {
 const video=document.getElementById('video');
 const placeholder=document.getElementById('videoPlaceholder');
 const result=document.getElementById('resultBody');
 const heading=document.querySelector('#scanResult h2');
 let reader=null, controls=null, lastValue='', lastAt=0;
 async function lookup(value){
  value=(value||'').trim(); if(!value)return;
  heading.textContent='Looking up '+value+'…';
  try{
   const res=await fetch('/api/lookup/'+encodeURIComponent(value),{headers:{'Accept':'application/json'}});
   const d=await res.json();
   if(!res.ok||!d.found)throw new Error('No registered copy found for barcode / ACC.NO '+value+'.');
   heading.textContent=d.title;
   result.replaceChildren();
   const info=document.createElement('div');info.className='history-item';
   const b=document.createElement('b');b.textContent='ACC.NO '+d.acc_no;
   const st=document.createElement('span');st.textContent='Status: '+d.status+' · Condition: '+d.condition;
   const small=document.createElement('small');small.textContent=(d.author||'Author not recorded')+(d.borrower?' · Borrowed by '+d.borrower+' · Due '+d.due:'');
   info.append(b,st,small);
   const link=document.createElement('a');link.className='btn btn-small';link.href=d.url;link.textContent='Open book passport →';
   result.append(info,link);
   document.getElementById('manualAcc').value=value;
  }catch(err){heading.textContent='No matching record';result.textContent=err.message;}
 }
 document.getElementById('manualLookup').addEventListener('submit',e=>{e.preventDefault();lookup(document.getElementById('manualAcc').value);});
 document.getElementById('startScan').addEventListener('click',async()=>{
  if(!window.ZXing){alert('Barcode engine did not load. Check internet access or use manual ACC.NO lookup.');return;}
  try{
   const formats=[ZXing.BarcodeFormat.CODE_128,ZXing.BarcodeFormat.CODE_39,ZXing.BarcodeFormat.EAN_13,ZXing.BarcodeFormat.EAN_8,ZXing.BarcodeFormat.ITF,ZXing.BarcodeFormat.CODABAR,ZXing.BarcodeFormat.UPC_A,ZXing.BarcodeFormat.UPC_E];
   const hints=new Map();hints.set(ZXing.DecodeHintType.POSSIBLE_FORMATS,formats);hints.set(ZXing.DecodeHintType.TRY_HARDER,true);
   reader=new ZXing.BrowserMultiFormatReader(hints,300);
   placeholder.style.display='none';
   controls=await reader.decodeFromConstraints({audio:false,video:{facingMode:{ideal:'environment'}}},video,(decoded)=>{
    if(decoded){const value=decoded.getText().trim(), now=Date.now();if(value!==lastValue||now-lastAt>1800){lastValue=value;lastAt=now;lookup(value);}}
   });
  }catch(err){placeholder.style.display='grid';alert('Could not start camera. Allow camera permission and use localhost/HTTPS. '+err.message);}
 });
 document.getElementById('stopScan').addEventListener('click',()=>{if(controls){controls.stop();controls=null;}if(reader){reader.reset();reader=null;}placeholder.style.display='grid';});
})();
